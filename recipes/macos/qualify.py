#!/usr/bin/env python3
"""Qualify changed native tools through the canonical disposable session owner."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

SPEC = importlib.util.spec_from_file_location('native_build', Path(__file__).with_name('build.py'))
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)

CONFIGURE = '''import json,hashlib,time,sys,os
from pathlib import Path
root=Path('/opt/ai-runner-qualification'); paths=json.loads(Path('/opt/ai-runner-images/toolchain-paths.json').read_text())
for name in ['qualification-session.py']:(root/name).chmod(0o755)
tools={'swiftlint':('/opt/ai-runner-images/bin/swiftlint',['version'],'0.65.1'),
       'python':(paths['python'],['--version'],'Python 3.12.14')}
config={'schema_version':1,'qualification_only':True,'image_export_permitted':False,
'repository':'uxmaltech-collab/ai-runner-images','recipe_commit':sys.argv[1],
'session_source_commit':'3a3e163793d85a2110a7de5098ffe2a2f90b2f3b','image':sys.argv[2],
'deadline_unix':int(time.time())+1200,'resources':json.loads(sys.argv[3]),
'guest_user':'qualifier','guest_home':'/Users/qualifier',
'session_policy':{'schema_version':2,'provisioner':{'name':'qualifier-setup','uid':501,'gid':20,'home':'/Users/qualifier-setup'},'runner':{'name':'qualifier','uid':502,'gid':20,'home':'/Users/qualifier'}},
'environment':{'PATH':'/opt/ai-runner-images/agents/bin:/opt/ai-runner-images/bin:'+paths['java_home']+'/bin:'+paths['node_bin']+':/usr/bin:/bin:/usr/sbin:/sbin','DEVELOPER_DIR':paths['developer_dir'],'JAVA_HOME':paths['java_home']},
'tools':{name:{'path':path,'sha256':hashlib.sha256(Path(path).resolve().read_bytes()).hexdigest(),'version_args':args,'version_contains':version} for name,(path,args,version) in tools.items()}}
(root/'qualification.json').write_text(json.dumps(config,indent=2)+'\\n'); (root/'qualification.json').chmod(0o644)
Path('/private/var/lib/ai-runner-qualification').mkdir(mode=0o700)
commands=root/'commands';commands.mkdir(mode=0o755);commands.chmod(0o755)
command={'tool':'python','args':['-I','-B',str(root/'swiftlint/qualify.py'),'--output','/Users/qualifier/swiftlint-qualification'],'cwd':'/Users/qualifier'}
(commands/'swiftlint.json').write_text(json.dumps(command)+'\\n');(commands/'swiftlint.json').chmod(0o644)
print(json.dumps({'configuration_sha256':hashlib.sha256((root/'qualification.json').read_bytes()).hexdigest(),'tools':config['tools']}))
'''


def qualify(build_result, work, root, binding_path, source_checkout, git='git'):
    result = json.loads(Path(build_result).read_text())
    if result['status'] != 'stopped-and-verified':
        raise ValueError('A finalized accountless artifact is required')
    root, work = Path(root).resolve(), Path(work).resolve()
    qualification_commit = subprocess.check_output([git, '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if subprocess.check_output([git, '-C', str(root), 'status', '--porcelain', '--',
        'recipes/macos', 'recipes/macos-xcode-maestro/swiftlint', 'recipes/qualification-session', 'scripts/tart-layer.py']).strip():
        raise ValueError('Qualification must use committed recipe sources')
    work.mkdir(mode=0o700)
    binding = json.loads(Path(binding_path).read_text())
    payload = work / 'session-payload'
    subprocess.run([sys.executable, '-B', str(root / 'recipes/qualification-session/prepare-payload.py'),
                    '--source-checkout', str(source_checkout), '--source-kind', 'templates',
                    '--output', str(payload), '--git', git], check=True)
    files = {p.relative_to(payload).as_posix(): p for p in payload.rglob('*') if p.is_file()}
    recipe = root / 'recipes/macos-xcode-maestro/swiftlint'
    for path in recipe.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and not path.name.startswith('test_'):
            files['swiftlint/' + path.relative_to(recipe).as_posix()] = path
    manifest = {name: {'bytes': p.stat().st_size, 'sha256': backend.sha(p)} for name, p in files.items()}
    backend.write(work / 'PAYLOAD.json', manifest)
    archive = work / 'payload.tar'
    with tarfile.open(archive, 'x') as package:
        for name, path in files.items():
            package.add(path, arcname=name, recursive=False)
        package.add(work / 'PAYLOAD.json', arcname='PAYLOAD.json')
    vm = Path(result['local_image']).name + '-qualification'
    owner = backend.Owner(root, work, binding_path, vm)
    report = {'schema_version': 1, 'image_manifest_sha256': result['image_manifest_sha256'],
              'image_recipe_commit': result['recipe_commit'], 'qualification_recipe_commit': qualification_commit,
              'github_job_created': False,
              'image_export_permitted': False, 'status': 'started'}
    parent_files = [Path(result['local_image']) / name for name in ('config.json', 'nvram.bin', 'disk.img')]
    parent_metadata = {str(p): (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns) for p in parent_files}
    active_boot, cloned = None, False
    try:
        owner.op('clone', 'clone', '--source', result['local_image'])
        cloned = True
        owner.op('boot-01', 'boot', '--timeout', '180')
        active_boot = work / 'boot-01.json'
        owner.execute('stage', [backend.PYTHON, '-I', '-B', '-c', backend.STAGE,
                               '/opt/ai-runner-qualification'], input_path=archive)
        resources = {'cpus': binding['cpu'], 'memory_mib': binding['memory_mib'],
                     'disk_gb': result['tuple']['disk.img']['bytes'] // 1000000000}
        owner.execute('configure', [backend.PYTHON, '-I', '-B', '-c', CONFIGURE, qualification_commit,
            'uxmaltech-collab/ai-runner-images/native@sha256:' + result['image_manifest_sha256'], json.dumps(resources)])
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
        report['session_receipt'] = backend.file_ref(status_path)
        owner.execute('lint', ['/bin/launchctl', 'asuser', '502', helper, 'gui-exec',
                              '/opt/ai-runner-qualification/commands/swiftlint.json'], timeout=240)
        output = owner.execute('result', ['/bin/cat', '/Users/qualifier/swiftlint-qualification/result.json'])
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
                exported = owner.execute('export-lint', ['/usr/bin/tar', '-czf', '-', '-C', '/Users/qualifier',
                                                       'swiftlint-qualification'], timeout=60)
                report['lint_evidence'] = backend.file_ref(exported)
            except BaseException as error:
                report['partial_evidence_export_error'] = str(error)
            try:
                owner.op('cleanup-stop', 'stop', '--boot-receipt', active_boot)
                active_boot = None
            except BaseException as error:
                report['cleanup_uncertainty'] = str(error)
        if cloned and active_boot is None:
            # The installed Tart owner deletes only this newly created disposable
            # child, after stopped state and the normal process exit were proved.
            argv = ['/usr/bin/sudo', '-n', '-u', binding['user'], '/usr/bin/env', '-i',
                    'HOME=' + binding['tart_child_home'], 'TART_HOME=' + binding['tart_home'],
                    'TART_NO_AUTO_PRUNE=1', 'PATH=' + binding['path'], binding['tart_binary'], 'delete', vm]
            process = subprocess.run(argv, capture_output=True, timeout=90)
            absent = not (Path(binding['tart_home']) / 'vms' / vm).exists()
            preserved = all(parent_metadata[str(p)] == (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns)
                            for p in parent_files)
            report['cleanup'] = {'argv': argv, 'exit_code': process.returncode,
                                 'owned_child_absent': absent, 'sealed_parent_preserved': preserved,
                                 'parent_metadata_before': parent_metadata,
                                 'stdout': process.stdout.decode('utf-8', 'replace'),
                                 'stderr': process.stderr.decode('utf-8', 'replace')}
            if process.returncode or not absent or not preserved:
                report['cleanup_uncertainty'] = 'Owned qualification VM deletion unconfirmed'
        if report.get('cleanup_uncertainty'):
            report['status'] = 'cleanup-unconfirmed'
        backend.write(work / 'QUALIFICATION-RESULT.json', report)
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
    parser.add_argument('--git', default='git')
    args = parser.parse_args()
    print(json.dumps(qualify(args.build_result, args.work, args.root, args.binding, args.source_checkout, args.git)))
