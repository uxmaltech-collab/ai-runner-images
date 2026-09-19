#!/usr/bin/env python3
"""Install all three pinned agents into a new builder guest layer, without auth."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import tempfile

RECIPE = Path(__file__).resolve().parent
PREFIX = Path('/opt/ai-runner-images/agents')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def verify(path, pin):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != pin['bytes']:
        raise ValueError(f'Unexpected payload type or size: {path}')
    if digest(path) != pin['sha256']:
        raise ValueError(f'Payload digest mismatch: {path}')


def launcher_bytes(engine, prefix=PREFIX):
    wrapper = '#!/bin/sh\n'
    if engine == 'claude':
        wrapper += 'export DISABLE_AUTOUPDATER=1\n'
    wrapper += f'exec {prefix}/{engine}/{engine} "$@"\n'
    return wrapper.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--codex-binary', type=Path, required=True)
    parser.add_argument('--codex-companion', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--verify-inputs-only', action='store_true')
    args = parser.parse_args()
    pins_raw = (RECIPE / 'pins.json').read_bytes()
    pins = json.loads(pins_raw)
    entries = [
        ('codex/codex', args.codex_binary, pins['codex']['binary']),
        ('codex/codex-code-mode-host', args.codex_companion, pins['codex']['companion']),
        ('claude/claude', args.artifacts / pins['claude']['file'], pins['claude']),
        ('grok/grok', args.artifacts / pins['grok']['file'], pins['grok']),
    ]
    if args.receipt.exists():
        raise ValueError('Receipt already exists; reconcile the completed or partial operation.')
    for _, source, pin in entries:
        verify(source, pin)
    receipt = {'schema_version': 1, 'operation': 'native-agent-layer-input-verification',
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'engines': pins['engines'], 'pins_sha256': hashlib.sha256(pins_raw).hexdigest(),
        'installed': False, 'binary_execution': False, 'network_calls': 0,
        'source_files': [{'path': str(source), 'destination': str(PREFIX / target),
            'bytes': pin['bytes'], 'sha256': pin['sha256']} for target, source, pin in entries]}
    if not args.verify_inputs_only:
        if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.geteuid() != 0:
            raise ValueError('Installation runs as root inside the declared macOS arm64 builder guest.')
        if PREFIX.exists() or PREFIX.is_symlink():
            raise ValueError('Agent layer already exists; preserve it and reconcile its receipt.')
        if not PREFIX.parent.exists():
            PREFIX.parent.mkdir(mode=0o755)
            PREFIX.parent.chmod(0o755)
        for parent in (PREFIX.parent, *PREFIX.parent.parents):
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError(f'Unprotected installation parent: {parent}')
        stage = Path(tempfile.mkdtemp(prefix='.agents-incoming-', dir=PREFIX.parent))
        # Leave the staging directory on error for inspection; never erase an older layer.
        stage.chmod(0o755)
        for target, source, pin in entries:
            destination = stage / target
            destination.parent.mkdir(mode=0o755, exist_ok=True)
            destination.parent.chmod(0o755)
            shutil.copyfile(source, destination)
            verify(destination, pin)
            destination.chmod(0o755)
        (stage / 'bin').mkdir(mode=0o755)
        (stage / 'bin').chmod(0o755)
        for engine in pins['engines']:
            (stage / 'bin' / engine).write_bytes(launcher_bytes(engine))
            (stage / 'bin' / engine).chmod(0o755)
        (stage / 'pins.json').write_bytes(pins_raw)
        (stage / 'pins.json').chmod(0o644)
        os.rename(stage, PREFIX)
        receipt.update(operation='native-agent-layer-installation', installed=True,
            prefix=str(PREFIX), runtime_path=str(PREFIX / 'bin'),
            configuration_or_credentials_created=False)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'installed': receipt['installed'], 'engines': pins['engines'],
        'receipt': str(args.receipt), 'receipt_sha256': digest(args.receipt)}, sort_keys=True))


if __name__ == '__main__':
    main()
