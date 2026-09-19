"""Shared host-side receipts, payload packing and the existing Tart owner client."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

POLICY = json.loads((Path(__file__).resolve().parents[1] / 'qualification-session/native-tools-policy.json').read_text())
PYTHON = POLICY['python']['path']


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


def pack(entries, work):
    manifest = {name: {'bytes': path.stat().st_size, 'sha256': sha(path)} for name, path in entries.items()}
    write(work / 'PAYLOAD.json', manifest)
    archive = work / 'payload.tar'
    with tarfile.open(archive, 'x') as package:
        for name, path in sorted(entries.items()):
            package.add(path, arcname=name, recursive=False)
        package.add(work / 'PAYLOAD.json', arcname='PAYLOAD.json')
    return archive


def stage_command(root, destination):
    # The bootstrap executes these versioned bytes before the payload exists.
    script = (root / 'recipes/macos/stage_payload.py').read_text()
    return [PYTHON, '-I', '-B', '-c', script, destination]
