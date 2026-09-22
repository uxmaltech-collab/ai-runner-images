#!/usr/bin/env python3
"""Remove inherited Runner logs in an accountless disposable image builder."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


def inventory(root):
    """Inspect metadata only; diagnostic contents may never enter evidence."""
    entries = []
    if not root.exists() and not root.is_symlink():
        return entries
    def visit(path):
        info = path.lstat()
        if (info.st_uid != os.geteuid() or stat.S_ISLNK(info.st_mode)
                or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
                or stat.S_ISREG(info.st_mode) and info.st_nlink != 1):
            raise ValueError('Unexpected diagnostic entry; preserve the builder')
        if path == root and not stat.S_ISDIR(info.st_mode):
            raise ValueError('Runner diagnostics must be a directory')
        entries.append((path, info.st_dev, info.st_ino, info.st_mode,
                        info.st_size, info.st_mtime_ns, info.st_ctime_ns))
        if stat.S_ISDIR(info.st_mode):
            for child in sorted(path.iterdir()):
                visit(child)
    visit(root)
    return entries


def remove_diagnostics(root, before):
    if inventory(root) != before:
        raise ValueError('Diagnostic metadata changed; preserve the builder')
    for path, _, _, mode, *_ in reversed(before):
        if stat.S_ISDIR(mode):
            path.rmdir()
        else:
            path.unlink()


def builder_preflight():
    if os.geteuid() != 0 or sys.platform != 'darwin':
        raise ValueError('Root in a disposable macOS builder is required')
    model = subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'], text=True).strip()
    if not model.startswith('VirtualMac'):
        raise ValueError('A virtual builder is required')
    users = subprocess.check_output(['/usr/bin/dscl', '.', '-list', '/Users', 'UniqueID'], text=True)
    if any(501 <= int(row.split()[-1]) < 60000 for row in users.splitlines()):
        raise ValueError('The builder must remain accountless')
    if Path('/private/etc/kcpassword').exists():
        raise ValueError('An autologin session must not be present')
    commands = subprocess.check_output(['/bin/ps', '-axo', 'comm='], text=True)
    if any(Path(line.strip()).name in {'Runner.Listener', 'Runner.Worker'} for line in commands.splitlines()):
        raise ValueError('An active runner must never be interrupted')


def runner_pin(root, expected):
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_relative_to('/opt'):
        raise ValueError('A canonical image-owned Runner path is required')
    binary = root / 'bin/Runner.Listener'
    if binary.parent.resolve(strict=True) != binary.parent:
        raise ValueError('Runner executable parent must not contain a symlink')
    for parent in (binary.parent, *binary.parent.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unprotected Runner template')
    if any((root / name).exists() or (root / name).is_symlink()
           for name in ('.runner', '.credentials', '.credentials_rsaparams', '.service')):
        raise ValueError('A configured Runner template must be preserved')
    info = binary.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
        raise ValueError('Unprotected Runner executable')
    with binary.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise ValueError('Runner executable differs from its declared hash')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner-root', type=Path, required=True)
    parser.add_argument('--runner-sha256', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    builder_preflight()
    pin = runner_pin(args.runner_root, args.runner_sha256)
    root = args.runner_root / '_diag'
    before = inventory(root)
    result = {'schema_version': 1, 'operation': 'clean-runner-diagnostics',
              'runner_root': str(args.runner_root), 'runner_sha256': pin,
              'diagnostic_entries': len(before), 'diagnostic_contents_read': False,
              'runtime_admission': False, 'status': 'started'}
    # Preserve the started claim separately. Either file fences repetition.
    started = args.receipt.with_suffix('.started.json')
    if args.receipt.exists() or args.receipt.is_symlink():
        raise ValueError('Existing receipt must be reconciled')
    with started.open('x') as output:
        json.dump(result, output, sort_keys=True); output.write('\n')
        output.flush(); os.fsync(output.fileno())
    remove_diagnostics(root, before)
    runner_pin(args.runner_root, pin)
    result.update(status='complete', diagnostic_directory_absent=not root.exists())
    with args.receipt.open('x') as output:
        json.dump(result, output, sort_keys=True); output.write('\n')
        output.flush(); os.fsync(output.fileno())
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
