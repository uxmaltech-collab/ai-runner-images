#!/usr/bin/env python3
"""Compose local Tart images through the existing layer owner; never admit them."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tarfile

PYTHON = '/opt/macos-tart-bootstrap/python/bin/python3.12'
LAYERS = ('macos-xcode-maestro', 'shared-agent-build', 'flutter-dart-ios')
PROFILES = ('macos-ios', 'macos-flutter')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def file_ref(path):
    path = Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def validate(inputs, profile):
    if profile not in PROFILES or inputs.get('schema_version') != 1:
        raise ValueError('Unsupported native profile or input schema')
    if set(inputs) - {'schema_version', 'name', 'binding', 'parent', 'artifacts', 'git', 'qualification'}:
        raise ValueError('Unknown native build inputs')
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,60}', inputs['name']):
        raise ValueError('Use a unique lowercase native build name')
    parent = inputs['parent']
    if set(parent) != {'directory', 'manifest', 'sha256', 'layer'} or parent['layer'] not in LAYERS:
        raise ValueError('A declared neutral parent layer and immutable tuple are required')
    if profile == 'macos-ios' and parent['layer'] == 'flutter-dart-ios':
        raise ValueError('Use an iOS base or shared-agent parent for the iOS profile')
    if not re.fullmatch('[0-9a-f]{64}', parent['sha256']):
        raise ValueError('Invalid parent manifest digest')
    required = {'swiftlint'}
    if parent['layer'] == 'macos-xcode-maestro':
        required |= {'codex', 'codex_companion', 'claude', 'grok'}
    if profile == 'macos-flutter' and parent['layer'] != 'flutter-dart-ios':
        required.add('flutter')
    if set(inputs['artifacts']) != required:
        raise ValueError(f'Provide exactly the required offline artifacts: {sorted(required)}')
    qualification = inputs['qualification']
    if (set(qualification) != {'source_checkout', 'source_kind'}
            or qualification['source_kind'] not in ('templates', 'consumer')):
        raise ValueError('Declare the existing locked canonical session source')
    for value in [inputs['binding'], parent['directory'], parent['manifest'],
                  qualification['source_checkout'], *inputs['artifacts'].values()]:
        if not Path(value).is_absolute():
            raise ValueError('Native input locations must be absolute')
    return required


def qualify_artifact(root, work, inputs):
    spec = importlib.util.spec_from_file_location('native_qualification', root / 'recipes/macos/qualify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = inputs['qualification']
    return module.qualify(work / 'ARTIFACT.json', work / 'qualification', root, work / 'binding.json',
                          source['source_checkout'], inputs.get('git', 'git'), source['source_kind'])


class Owner:
    """Receipts and bounded RPC remain owned by scripts/tart-layer.py."""
    def __init__(self, root, work, binding, vm):
        self.root, self.work, self.binding, self.vm = map(Path, (root, work, binding, vm))

    def op(self, name, operation, *args):
        receipt = self.work / (name + '.json')
        argv = [sys.executable, '-B', str(self.root / 'scripts/tart-layer.py'),
                '--binding', str(self.binding), '--receipt', str(receipt), '--vm', str(self.vm),
                operation, *map(str, args)]
        # The owner provides operation deadlines and preserves partial command output.
        with (self.work / (name + '.owner.stdout')).open('xb') as out, \
             (self.work / (name + '.owner.stderr')).open('xb') as err:
            process = subprocess.run(argv, stdout=out, stderr=err)
        if process.returncode:
            raise ValueError(f'Native owner failed; reconcile {receipt}')
        value = json.loads(receipt.read_text())
        if value['status'] != 'complete':
            raise ValueError(f'Incomplete native owner operation: {receipt}')
        return value

    def execute(self, name, command, *, timeout=120, input_path=None):
        args = ['--timeout', str(timeout)]
        if input_path:
            args += ['--input', str(input_path)]
        result = self.op(name, 'exec', *args, '--', *command)
        return Path(result['commands'][-1]['stdout']['path'])


def payload(root, work, artifacts):
    """Stage only versioned recipe bytes and explicitly supplied locked artifacts."""
    entries = {}
    for directory in ('macos', 'macos-xcode-maestro/swiftlint', 'agent-build', 'flutter-dart'):
        for path in (root / 'recipes' / directory).rglob('*'):
            if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts:
                if path.suffix in ('.py', '.json', '.swift', '.yml') and not path.name.startswith('test_'):
                    entries[path.relative_to(root).as_posix()] = path
    names = {'codex': 'codex', 'codex_companion': 'codex-code-mode-host',
             'claude': 'claude-2.1.266-darwin-arm64', 'grok': 'grok-1.0.24-macos-aarch64',
             'swiftlint': 'portable_swiftlint.zip', 'flutter': 'flutter.zip'}
    for name, source in artifacts.items():
        path = Path(source)
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('Artifact must be a regular file')
        entries['artifacts/' + names[name]] = path
    manifest = {name: {'bytes': path.stat().st_size, 'sha256': sha(path)} for name, path in entries.items()}
    write(work / 'PAYLOAD.json', manifest)
    with tarfile.open(work / 'payload.tar', 'x') as package:
        for name, path in sorted(entries.items()):
            package.add(path, arcname=name, recursive=False)
        package.add(work / 'PAYLOAD.json', arcname='PAYLOAD.json')
    return work / 'payload.tar'


STAGE = '''import sys,tarfile,json,hashlib,os
from pathlib import Path
root=Path(sys.argv[1]); root.mkdir(mode=0o755); root.chmod(0o755)
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|') as package:
 for item in package:
  if not (item.isfile() or item.isdir()) or Path(item.name).is_absolute() or '..' in Path(item.name).parts: raise ValueError('Invalid payload member')
  package.extract(item,root,filter='data')
for directory,dirs,files in os.walk(root):
 Path(directory).chmod(0o755)
 for name in files:
  path=Path(directory)/name; path.chmod(0o644); os.chown(path,0,0)
manifest=json.loads((root/'PAYLOAD.json').read_text())
for name,pin in manifest.items():
 path=root/name
 with path.open('rb') as stream: actual=hashlib.file_digest(stream,'sha256').hexdigest()
 assert path.stat().st_size==pin['bytes'] and actual==pin['sha256'],name
print(json.dumps({'verified_files':len(manifest),'credentials_transferred':False}))
'''


def build(inputs, work, root, commit, *, profile):
    """Return a JSON-serializable stopped local artifact receipt for the front end.

    ``inputs`` is the native object documented in README.md, ``work`` is a fresh
    evidence directory, ``root`` is the committed Images checkout. No checkpoint
    Python, network download, executor/RPC installation or remote registry is used.
    """
    validate(inputs, profile)
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('The native backend requires macOS arm64')
    root, work = Path(root).resolve(), Path(work).resolve()
    git = inputs.get('git', 'git')
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('An exact recipe commit is required')
    head = subprocess.check_output([git, '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    changed = subprocess.check_output([git, '-C', str(root), 'status', '--porcelain', '--',
                                       'recipes/macos', 'recipes/macos-xcode-maestro/swiftlint',
                                       'recipes/agent-build', 'recipes/flutter-dart', 'scripts/tart-layer.py'])
    if head != commit or changed.strip():
        raise ValueError('Native recipe inputs must match the committed checkout')
    if work.exists():
        # The canonical front end exclusively creates work and writes PLAN.json
        # before delegation. Accept only that fresh, matching handoff.
        if sorted(path.name for path in work.iterdir()) != ['PLAN.json']:
            raise FileExistsError('Existing native evidence must be reconciled')
        plan = json.loads((work / 'PLAN.json').read_text())
        if (plan.get('profile') != profile or plan.get('source_commit') != commit
                or plan.get('backend') != 'recipes/macos/build.py'
                or plan.get('work_dir') != str(work) or plan.get('source_clean') is not True):
            raise ValueError('Front-end plan does not match this native build')
    else:
        work.mkdir(mode=0o700)
    write(work / 'INPUTS.json', inputs)
    binding = json.loads(Path(inputs['binding']).read_text())
    write(work / 'binding.json', binding)
    parent = inputs['parent']
    manifest = Path(parent['manifest'])
    if sha(manifest) != parent['sha256']:
        raise ValueError('Parent manifest differs from the declared identity')
    source = Path(parent['directory'])
    files = json.loads(manifest.read_text())['files']
    if set(files) != {'config.json', 'disk.img', 'nvram.bin'}:
        raise ValueError('A complete physical parent tuple is required')
    # Hash immutable parent bytes once; clone owner then locks and checks no holders.
    before = {}
    for name, pin in files.items():
        path = source / name
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != pin.get('bytes', pin.get('size')) or sha(path) != pin['sha256']:
            raise ValueError(f'Parent tuple differs from manifest: {name}')
        before[name] = (info.st_ino, info.st_size, info.st_mtime_ns)
    write(work / 'PARENT-VERIFIED.json', {'physical_parent': parent, 'files': files, 'metadata': before})
    archive = payload(root, work, inputs['artifacts'])
    owner = Owner(root, work, work / 'binding.json', inputs['name'])
    stage = '/opt/ai-runner-build-' + inputs['name']
    result = {'schema_version': 1, 'profile': profile, 'recipe_commit': commit,
              'physical_parent': parent, 'status': 'started', 'distribution': 'local-only',
              'runtime_admission': False, 'remote_restore_verified': False,
              'qualification': 'pending-disposable-nonadministrator-session',
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    boot = None
    try:
        owner.op('clone', 'clone', '--source', source)
        for name, metadata in before.items():
            info = (source / name).stat()
            if metadata != (info.st_ino, info.st_size, info.st_mtime_ns):
                raise ValueError('Physical parent changed around cloning')
        boot = owner.op('boot', 'boot', '--timeout', '180')
        owner.execute('stage', [PYTHON, '-I', '-B', '-c', STAGE, stage], input_path=archive, timeout=300)
        output = owner.execute('install', [PYTHON, '-I', '-B', stage + '/recipes/macos/guest.py',
                                          '--root', stage, '--profile', profile, '--parent-layer', parent['layer'],
                                          '--commit', commit], timeout=1800)
        result['components'] = json.loads(output.read_text())
        exported = owner.execute('export', ['/usr/bin/tar', '-czf', '-', '-C', stage, 'evidence'], timeout=120)
        result['component_evidence'] = file_ref(exported)
        owner.execute('remove-stage', [PYTHON, '-I', '-B', '-c',
            'import shutil,sys; from pathlib import Path; p=Path(sys.argv[1]); '
            'assert p.parent==Path("/opt") and p.name.startswith("ai-runner-build-"); shutil.rmtree(p)', stage])
        owner.op('stop', 'stop', '--boot-receipt', work / 'boot.json')
        boot = None
        sealed = owner.op('seal', 'seal', '--shutdown-receipt', work / 'stop.json',
                          '--source-commit', commit, '--parent-manifest', manifest, '--parent-digest', parent['sha256'])
        result.update(status='passed', artifact_state='stopped-and-verified', image_manifest=file_ref(sealed['manifest_path']),
                      image_manifest_sha256=sealed['manifest_sha256'], tuple=sealed['manifest']['files'],
                      local_image=str(Path(binding['tart_home']) / 'vms' / inputs['name']),
                      original_parent_preserved=True)
        write(work / 'ARTIFACT.json', result)
        result['qualification'] = qualify_artifact(root, work, inputs)
        if result['qualification'].get('status') != 'passed':
            raise ValueError('Native qualification did not pass; preserved artifact remains unadmitted')
        result['cleanup'] = result['qualification']['cleanup']
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error))
        if boot:
            try:
                owner.op('failure-stop', 'stop', '--boot-receipt', work / 'boot.json')
                result['failed_builder_stopped'] = True
            except BaseException as cleanup:
                result['cleanup_uncertainty'] = str(cleanup)
        if isinstance(error, Exception) and not isinstance(error, (OSError, ValueError, KeyError, subprocess.SubprocessError)):
            # Preserve the detailed native result while using the front end's
            # documented failure types so it also writes RESULT.json.
            raise ValueError(f'Native build failed: {error}; evidence: {work}') from error
        raise
    finally:
        result['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(work / 'BUILD-RESULT.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--commit', required=True)
    parser.add_argument('--profile', choices=PROFILES, required=True)
    args = parser.parse_args()
    print(json.dumps(build(json.loads(args.inputs.read_text()), args.work, args.root, args.commit, profile=args.profile)))
