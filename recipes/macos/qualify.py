#!/usr/bin/env python3
"""Qualify changed native tools through the canonical disposable session owner."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from recipes.macos.host import Owner, POLICY, PYTHON, file_ref, pack, stage_command, write
from recipes.macos.budgets import stage_budget


def qualify(build_result, work, root, binding_path, source_checkout, git='git', source_kind='templates'):
    result = json.loads(Path(build_result).read_text())
    if result.get('artifact_state') != 'stopped-and-verified':
        raise ValueError('A finalized accountless artifact is required')
    root, work = Path(root).resolve(), Path(work).resolve()
    qualification_commit = subprocess.check_output([git, '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if subprocess.check_output([git, '-C', str(root), 'status', '--porcelain', '--',
        'recipes/macos', 'recipes/macos-xcode-maestro/swiftlint', 'recipes/qualification-session', 'scripts/tart-layer.py']).strip():
        raise ValueError('Qualification must use committed recipe sources')
    work.mkdir(mode=0o700)
    binding = json.loads(Path(binding_path).read_text())
    payload = work / 'session-payload'
    command = [sys.executable, '-B', str(root / 'recipes/qualification-session/prepare-payload.py'),
               '--source-checkout', str(source_checkout), '--source-kind', source_kind,
               '--output', str(payload), '--git', git]
    with (work / 'payload-preparation.stdout').open('xb') as out, (work / 'payload-preparation.stderr').open('xb') as err:
        preparation = subprocess.run(command, stdout=out, stderr=err, timeout=90)
    write(work / 'PAYLOAD-PREPARATION.json', {'argv': command, 'exit_code': preparation.returncode,
        'stdout': file_ref(work / 'payload-preparation.stdout'),
        'stderr': file_ref(work / 'payload-preparation.stderr'), 'vm_created': False})
    if preparation.returncode:
        raise RuntimeError('Canonical session payload preparation failed; original output retained')
    files = {p.relative_to(payload).as_posix(): p for p in payload.rglob('*') if p.is_file()}
    recipe = root / 'recipes/macos-xcode-maestro/swiftlint'
    for path in recipe.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and not path.name.startswith('test_'):
            files['swiftlint/' + path.relative_to(recipe).as_posix()] = path
    for name in ('configure-native-tools.py', 'native-tools-policy.json'):
        files[name] = root / 'recipes/qualification-session' / name
    archive = pack(files, work)
    vm = Path(result['local_image']).name + '-qualification'
    owner = Owner(root, work, binding_path, vm)
    report = {'schema_version': 1, 'image_manifest_sha256': result['image_manifest_sha256'],
              'image_recipe_commit': result['recipe_commit'], 'qualification_recipe_commit': qualification_commit,
              'github_job_created': False,
              'image_export_permitted': False, 'status': 'started'}
    parent_files = [Path(result['local_image']) / name for name in ('config.json', 'nvram.bin', 'disk.img')]
    parent_metadata = {str(p): (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns) for p in parent_files}
    active_boot, cloned = None, False
    runner = POLICY['session_policy']['runner']
    try:
        owner.op('clone', 'clone', '--source', result['local_image'])
        cloned = True
        owner.op('boot-01', 'boot', '--timeout', '180')
        active_boot = work / 'boot-01.json'
        owner.execute('stage', stage_command(root, '/opt/ai-runner-qualification'),
                      input_path=archive, timeout=stage_budget(archive.stat().st_size))
        resources = {'cpus': binding['cpu'], 'memory_mib': binding['memory_mib'],
                     'disk_gb': result['tuple']['disk.img']['bytes'] // 1000000000}
        owner.execute('configure', [PYTHON, '-I', '-B',
            '/opt/ai-runner-qualification/configure-native-tools.py', qualification_commit,
            POLICY['repository'] + '/native@sha256:' + result['image_manifest_sha256'], json.dumps(resources)])
        helper = '/opt/ai-runner-qualification/qualification-session.py'
        answer = owner.execute('prepare', [helper, 'prepare'], timeout=180)
        prepared = json.loads(answer.read_text())
        if prepared.get('status') != 'session-prepared' or not prepared.get('reboot_required'):
            raise RuntimeError('Canonical session preparation did not complete')
        # The same image owner performs a normal guest shutdown and confirms its
        # Tart process exit. No account transaction is repeated across this boot.
        owner.op('session-stop', 'stop', '--boot-receipt', active_boot)
        active_boot = None
        owner.op('boot-02', 'boot', '--timeout', '180')
        active_boot = work / 'boot-02.json'
        for attempt in range(1, 7):
            status_path = owner.execute(f'status-{attempt}', [helper, 'status'], timeout=180)
            status = json.loads(status_path.read_text())
            if status.get('status') == 'ready':
                break
            time.sleep(5)
        else:
            raise RuntimeError('Nonadministrator Aqua readiness was not demonstrated')
        report['session_receipt'] = file_ref(status_path)
        owner.execute('lint', ['/bin/launchctl', 'asuser', str(runner['uid']), helper, 'gui-exec',
                              '/opt/ai-runner-qualification/commands/swiftlint.json'], timeout=240)
        output = owner.execute('result', ['/bin/cat', runner['home'] + '/swiftlint-qualification/result.json'])
        report['lint'] = json.loads(output.read_text())
        if report['lint']['status'] != 'passed':
            raise RuntimeError('Real lint fixtures did not pass')
        report['status'] = 'passed'
    except BaseException as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if active_boot:
            try:
                exported = owner.execute('export-lint', ['/usr/bin/tar', '-czf', '-', '-C', runner['home'],
                                                       'swiftlint-qualification'], timeout=60)
                report['lint_evidence'] = file_ref(exported)
            except BaseException as error:
                report['partial_evidence_export_error'] = str(error)
            try:
                owner.op('cleanup-stop', 'stop', '--boot-receipt', active_boot)
                active_boot = None
            except BaseException as error:
                report['cleanup_uncertainty'] = str(error)
        if cloned and active_boot is None:
            try:
                owner.op('cleanup-delete', 'delete')
                absent = not (Path(binding['tart_home']) / 'vms' / vm).exists()
                preserved = all(parent_metadata[str(p)] == (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns)
                                for p in parent_files)
                report['cleanup'] = {'owner_receipt': file_ref(work / 'cleanup-delete.json'),
                                     'owned_child_absent': absent, 'sealed_parent_preserved': preserved,
                                     'parent_metadata_before': parent_metadata}
                if not absent or not preserved:
                    raise RuntimeError('Owned child absence or sealed parent preservation unconfirmed')
            except BaseException as error:
                report['cleanup_uncertainty'] = str(error)
        if report.get('cleanup_uncertainty'):
            report['status'] = 'cleanup-unconfirmed'
        write(work / 'QUALIFICATION-RESULT.json', report)
    if report.get('cleanup_uncertainty'):
        raise RuntimeError(report['cleanup_uncertainty'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-result', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--source-checkout', type=Path, required=True)
    parser.add_argument('--source-kind', choices=['templates', 'consumer'], default='templates')
    parser.add_argument('--git', default='git')
    args = parser.parse_args()
    print(json.dumps(qualify(args.build_result, args.work, args.root, args.binding, args.source_checkout, args.git, args.source_kind)))
