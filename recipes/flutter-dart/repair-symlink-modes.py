#!/usr/bin/env python3
"""Repair public SDK symlink modes in a new accountless image derivative.

Preserve the sealed parent. This verifies existing bytes and link targets, changes
only link modes and SDK metadata, and does not extract or precache Flutter again.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess

RECIPE = Path(__file__).resolve().parent
PREFIX = Path('/opt/ai-runner-images/flutter')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, raw, mode):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def verify_seed(root, entries):
    """Verify the old manifest completely before any image mutation."""
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o555:
        raise ValueError('Unexpected sealed SDK root.')
    expected, links, total_bytes, files = set(), [], 0, 0
    for entry in entries:
        relative = PurePosixPath(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or str(relative) in ('', '.'):
            raise ValueError('Unsafe SDK manifest path.')
        if relative.as_posix() in expected:
            raise ValueError('Duplicate SDK manifest path.')
        expected.add(relative.as_posix())
        path = root / relative
        for parent in path.parents:
            if parent == root:
                break
            parent_info = parent.lstat()
            if not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != 0 or parent_info.st_mode & 0o022:
                raise ValueError('SDK entry has an unprotected or symlinked parent.')
        info = path.lstat()
        if info.st_uid != 0 or info.st_gid != 0:
            raise ValueError('Unexpected SDK owner.')
        if entry['kind'] == 'file':
            if (not stat.S_ISREG(info.st_mode) or info.st_size != entry['bytes']
                    or stat.S_IMODE(info.st_mode) != entry['mode']
                    or file_digest(path) != entry['sha256']):
                raise ValueError('Existing SDK file differs from the preserved manifest.')
            total_bytes += info.st_size
            files += 1
        elif entry['kind'] == 'directory':
            if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o555:
                raise ValueError('Unexpected sealed SDK directory.')
        elif entry['kind'] == 'symlink':
            if not stat.S_ISLNK(info.st_mode) or os.readlink(path) != entry['target']:
                raise ValueError('Existing SDK link target differs from the preserved manifest.')
            if 'mode' in entry and stat.S_IMODE(info.st_mode) != entry['mode']:
                raise ValueError('Existing SDK link mode differs from the preserved manifest.')
            if Path(entry['target']).is_absolute() or not path.resolve().is_relative_to(root):
                raise ValueError('SDK link target escapes the sealed seed.')
            links.append((path, entry, stat.S_IMODE(info.st_mode)))
        else:
            raise ValueError('Unexpected SDK manifest entry type.')
    actual = {str((Path(parent) / name).relative_to(root))
              for parent, directories, names in os.walk(root, followlinks=False)
              for name in directories + names}
    if actual != expected:
        raise ValueError('SDK inventory differs from the preserved manifest.')
    return links, files, total_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--expected-ready-sha256', required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.getuid() != 0:
        raise ValueError('Repair requires root in the declared Darwin arm64 derivative.')
    if not subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'], text=True).startswith('VirtualMac'):
        raise ValueError('Repair must run inside the owned virtual guest.')
    users = subprocess.check_output(['/usr/bin/dscl', '.', '-list', '/Users', 'UniqueID'], text=True)
    if any(int(row.split()[-1]) >= 500 for row in users.splitlines()):
        raise ValueError('Repair requires a new accountless derivative, not a qualification or job VM.')
    for parent in (PREFIX, *PREFIX.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unprotected Flutter installation parent.')
    pins = json.loads((RECIPE / 'pins.json').read_bytes())
    version = PREFIX / pins['flutter_version']
    version_info = version.lstat()
    if (not stat.S_ISDIR(version_info.st_mode) or version_info.st_uid != 0
            or stat.S_IMODE(version_info.st_mode) != 0o555):
        raise ValueError('Unexpected sealed SDK version directory.')
    ready_path, manifest_path = version / 'SDK-READY.json', version / 'SDK-MANIFEST.json'
    for path in (ready_path, manifest_path):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o444:
            raise ValueError('Unexpected protected SDK metadata.')
    ready_raw, manifest_raw = ready_path.read_bytes(), manifest_path.read_bytes()
    ready, manifest = json.loads(ready_raw), json.loads(manifest_raw)
    if digest(ready_raw) != args.expected_ready_sha256 or digest(manifest_raw) != ready['manifest_sha256']:
        raise ValueError('SDK metadata does not match the declared preserved seed.')
    if (ready['status'] != 'precache-complete-and-sealed'
            or any(ready[name] != pins[name] for name in ('flutter_version', 'flutter_revision', 'dart_version'))
            or ready['archive_sha256'] != pins['archive']['sha256']):
        raise ValueError('SDK identity does not match the pinned recipe.')
    links, files, total_bytes = [], 0, 0
    for section, directory in [('sdk', 'sdk'), ('pub_cache_seed', 'pub-cache-seed')]:
        found, count, size = verify_seed(version / directory, manifest[section])
        links.extend(found)
        files += count
        total_bytes += size
    if not args.evidence_dir.is_absolute() or args.evidence_dir.exists():
        raise ValueError('Provide a new absolute private evidence directory.')
    for parent in args.evidence_dir.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Unprotected evidence parent.')
    args.evidence_dir.mkdir(mode=0o700)
    args.evidence_dir.chmod(0o700)
    write_new(args.evidence_dir / 'SDK-READY.before.json', ready_raw, 0o600)
    write_new(args.evidence_dir / 'SDK-MANIFEST.before.json', manifest_raw, 0o600)
    result = {'schema_version': 1, 'operation': 'repair-public-sdk-symlink-modes',
        'started_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'verified-before-mutation', 'previous_ready_sha256': digest(ready_raw),
        'previous_manifest_sha256': digest(manifest_raw),
        'verified_regular_files': files, 'verified_regular_file_bytes': total_bytes,
        'links': [{'path': str(path.relative_to(version)), 'target': entry['target'],
                   'before': oct(mode), 'after': '0o555'} for path, entry, mode in links],
        'extraction_repeated': False, 'precache_repeated': False, 'accounts_created': False,
        'network_calls': 0, 'regular_file_contents_changed': False}
    write_new(args.evidence_dir / 'REPAIR-INTENT.json', json_bytes(result), 0o600)
    for path, entry, _ in links:
        os.chmod(path, 0o555, follow_symlinks=False)
        if stat.S_IMODE(path.lstat().st_mode) != 0o555 or os.readlink(path) != entry['target']:
            raise ValueError('Symlink mode readback failed; reconcile the preserved repair intent.')
        entry['mode'] = 0o555
    new_manifest = json_bytes(manifest)
    ready['manifest_sha256'] = digest(new_manifest)
    new_ready = json_bytes(ready)
    for path, raw in [(manifest_path, new_manifest), (ready_path, new_ready)]:
        temporary = path.with_name('.' + path.name + '.symlink-repair')
        write_new(temporary, raw, 0o444)
        os.replace(temporary, path)
    if manifest_path.read_bytes() != new_manifest or ready_path.read_bytes() != new_ready:
        raise ValueError('SDK metadata readback failed; reconcile the preserved repair intent.')
    result.update(status='complete', finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sdk_manifest_sha256=digest(new_manifest), sdk_ready_sha256=digest(new_ready),
        nonadministrator_qualification='pending-in-disposable-qualification-clone')
    write_new(args.evidence_dir / 'REPAIR-RECEIPT.json', json_bytes(result), 0o600)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
