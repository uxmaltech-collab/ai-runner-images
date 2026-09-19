#!/usr/bin/env python3
"""Install locked SwiftLint bytes offline in an owned macOS builder guest."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import tempfile
import zipfile

RECIPE = Path(__file__).resolve().parent
LAYOUTS = {
    'neutral': ('/opt/ai-runner-images/tools/swiftlint/{version}', '/opt/ai-runner-images/bin'),
    'consumer': ('/opt/macos-tart-bootstrap/resolver-tools/swiftlint-{version}',
                 '/opt/ai-repo-resources/python/bin'),
}


def layout(name, pins):
    return tuple(Path(path.format(version=pins['version'])) for path in LAYOUTS[name])


def launcher_bytes(prefix):
    return f'#!/bin/sh\nexec {prefix}/swiftlint "$@"\n'.encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verified_members(archive, pins):
    info = archive.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != pins['archive']['bytes']:
        raise ValueError('Archive must be a regular file with the locked size')
    raw = archive.read_bytes()
    if digest(raw) != pins['archive']['sha256']:
        raise ValueError('Archive digest mismatch')
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        names = package.namelist()
        if sorted(names) != sorted(pins['members']):
            raise ValueError('Archive members differ from the exact lock')
        result = {}
        for name, pin in pins['members'].items():
            member = package.getinfo(name)
            mode = member.external_attr >> 16
            if member.file_size != pin['bytes'] or stat.S_ISLNK(mode):
                raise ValueError('Unexpected archive member type or size')
            data = package.read(member)
            if len(data) != pin['bytes'] or digest(data) != pin['sha256']:
                raise ValueError('Extracted member digest mismatch')
            result[name] = data
    return result


def protected_directory(path):
    if not path.is_absolute():
        raise ValueError('Absolute installation paths are required')
    for parent in reversed((path, *path.parents)):
        if not parent.exists() and not parent.is_symlink():
            parent.mkdir(mode=0o755)
            parent.chmod(0o755)  # Do not inherit the operator's private umask.
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError(f'Unprotected installation directory: {parent}')
        if info.st_mode & 0o005 != 0o005:
            raise ValueError(f'Installation directory is inaccessible to the runner: {parent}')


def install(archive, pins, prefix, bin_dir):
    members = verified_members(archive, pins)
    launcher = bin_dir / 'swiftlint'
    if prefix.exists() or prefix.is_symlink() or launcher.exists() or launcher.is_symlink():
        raise ValueError('Existing installation must be reconciled, never overwritten')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', str(prefix)):
        raise ValueError('Unsupported launcher path')
    protected_directory(prefix.parent)
    protected_directory(bin_dir)
    stage = Path(tempfile.mkdtemp(prefix='.swiftlint-incoming-', dir=prefix.parent))
    stage.chmod(0o755)
    # Preserve a partial stage on failure; the owner decides recovery.
    for name, raw in members.items():
        target = stage / name
        with target.open('xb') as stream:
            stream.write(raw)
        target.chmod(int(pins['members'][name]['mode'], 8))
    os.rename(stage, prefix)
    wrapper = launcher_bytes(prefix)
    with launcher.open('xb') as stream:
        stream.write(wrapper)
    launcher.chmod(0o755)
    files = []
    for path in [*(prefix / name for name in members), launcher]:
        info = path.lstat()
        files.append({'path': str(path), 'bytes': info.st_size,
                      'sha256': digest(path.read_bytes()), 'mode': f'{stat.S_IMODE(info.st_mode):04o}',
                      'uid': info.st_uid, 'gid': info.st_gid})
    return {'prefix': str(prefix), 'runtime_path': str(bin_dir), 'files': files}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--layout', choices=LAYOUTS, default='neutral')
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--verify-inputs-only', action='store_true')
    args = parser.parse_args()
    if args.receipt.exists():
        raise ValueError('Existing receipt must be reconciled')
    pins_raw = (RECIPE / 'pins.json').read_bytes()
    pins = json.loads(pins_raw)
    verified_members(args.archive, pins)
    receipt = {'schema_version': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'version': pins['version'], 'pins_sha256': digest(pins_raw),
               'archive': pins['archive'], 'layout': args.layout, 'installed': False,
               'network_calls': 0, 'credentials_created': False, 'binary_execution': False}
    if not args.verify_inputs_only:
        if os.geteuid() != 0 or platform.system() != 'Darwin' or platform.machine() != 'arm64':
            raise ValueError('Root inside the owned macOS arm64 builder guest is required')
        model = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'], text=True).strip()
        if not model.startswith('VirtualMac'):
            raise ValueError('Installation is restricted to the declared virtual builder')
        prefix, bin_dir = layout(args.layout, pins)
        receipt.update(install(args.archive, pins, prefix, bin_dir), installed=True)
    with args.receipt.open('x') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
