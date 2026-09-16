#!/usr/bin/env python3
"""Run Flutter/Dart using a private APFS clone of the protected SDK seed."""
import ctypes
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import sys
import tempfile

PREFIX = Path('/opt/ai-runner-images/flutter')
VERSION = '3.47.4'


def owned_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError(f'Expected a private user-owned directory: {path}')


def protected_file(path):
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError(f'Unprotected SDK parent: {parent}')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError(f'Unprotected SDK metadata: {path}')
    return path.read_bytes()


def clone_tree(source, destination):
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    clonefile = library.clonefile
    clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clonefile.restype = ctypes.c_int
    count = 0

    def clone_file(src, dst):
        nonlocal count
        # CLONE_NOOWNERCOPY (0x0002) gives every clone the caller's ownership.
        if clonefile(os.fsencode(src), os.fsencode(dst), 0x0002) != 0:
            error = ctypes.get_errno()
            raise OSError(error, 'APFS clonefile failed; use a writable location on the SDK filesystem', dst)
        count += 1
        return dst

    shutil.copytree(source, destination, symlinks=True, copy_function=clone_file)
    # A clone preserves read-only seed modes; only this user's new copy is made writable.
    for root, directories, files in os.walk(destination, followlinks=False):
        Path(root).chmod(0o700)
        for name in files:
            path = Path(root) / name
            info = path.lstat()
            if stat.S_ISREG(info.st_mode):
                path.chmod(0o700 if info.st_mode & 0o111 else 0o600)
    return count


def private_root(home):
    requested = os.environ.get('AI_RUNNER_FLUTTER_WORK_ROOT')
    if requested:
        root = Path(requested)
        if not root.is_absolute():
            raise ValueError('AI_RUNNER_FLUTTER_WORK_ROOT must be absolute.')
        root.mkdir(mode=0o700, exist_ok=True)
        owned_directory(root)
        return root
    root = home / 'Library' / 'Caches' / 'ai-runner-images'
    current = home
    owned_directory(current)
    for component in ('Library', 'Caches', 'ai-runner-images'):
        current = current / component
        current.mkdir(mode=0o700, exist_ok=True)
        owned_directory(current)
    return root


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('flutter', 'dart'):
        raise ValueError('Usage: launcher.py flutter|dart [arguments...]')
    if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.geteuid() == 0:
        raise ValueError('The writable SDK launcher runs as a non-root macOS arm64 job user.')
    home = Path(os.environ['HOME'])
    if not home.is_absolute() or home.resolve() != home:
        raise ValueError('HOME must be the canonical home of the current job account.')
    ready_raw = protected_file(PREFIX / VERSION / 'SDK-READY.json')
    ready = json.loads(ready_raw)
    if ready['flutter_version'] != VERSION or ready['status'] != 'precache-complete-and-sealed':
        raise ValueError('The installed SDK seed is incomplete.')
    seed_digest = hashlib.sha256(ready_raw).hexdigest()
    root = private_root(home)
    leaf = root / ('flutter-' + VERSION + '-' + seed_digest[:16])
    lock = root / ('.' + leaf.name + '.lock')
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if info.st_uid != os.geteuid() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError('Untrusted Flutter initialization lock.')
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if leaf.exists() or leaf.is_symlink():
            owned_directory(leaf)
            receipt_file = leaf / 'CLONE-RECEIPT.json'
            info = receipt_file.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
                raise ValueError('Missing or unsafe clone receipt; preserve and reconcile this directory.')
            receipt = json.loads(receipt_file.read_bytes())
            if receipt.get('seed_ready_sha256') != seed_digest or receipt.get('status') != 'ready':
                raise ValueError('Existing clone is incomplete; preserve it before explicit recovery.')
        else:
            stage = Path(tempfile.mkdtemp(prefix='.' + leaf.name + '.incoming-', dir=root))
            # No overwrite or automatic deletion: an interrupted clone is preserved for recovery.
            sdk_count = clone_tree(PREFIX / VERSION / 'sdk', stage / 'sdk')
            cache_count = clone_tree(PREFIX / VERSION / 'pub-cache-seed', stage / 'pub-cache')
            receipt = {'schema_version': 1, 'status': 'ready',
                'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'uid': os.getuid(), 'gid': os.getgid(), 'seed_ready_sha256': seed_digest,
                'flutter_version': VERSION, 'flutter_revision': ready['flutter_revision'],
                'method': 'clonefile(2)-without-copy-fallback',
                'sdk_regular_files_cloned': sdk_count, 'pub_cache_regular_files_cloned': cache_count}
            with (stage / 'CLONE-RECEIPT.json').open('x') as stream:
                json.dump(receipt, stream, indent=2, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.rename(stage, leaf)
    finally:
        os.close(descriptor)
    sdk = leaf / 'sdk'
    env = os.environ.copy()
    env.update(FLUTTER_ROOT=str(sdk), PUB_CACHE=str(leaf / 'pub-cache'),
        FLUTTER_SUPPRESS_ANALYTICS='true', DART_SUPPRESS_ANALYTICS='true')
    env['PATH'] = str(sdk / 'bin') + os.pathsep + env.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')
    tool = sys.argv[1]
    # Both tool invocations receive the supported suppress-analytics flag, even on first use.
    executable = sdk / 'bin' / tool
    os.execve(executable, [str(executable), '--suppress-analytics', *sys.argv[2:]], env)


if __name__ == '__main__':
    main()
