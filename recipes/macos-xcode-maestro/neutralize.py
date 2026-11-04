#!/usr/bin/env python3
"""Remove inventoried consumer/agent material from a new accountless builder copy.

The parent is preserved by the host COW operation. The removal targets and their
exact inventories come from the dated record of the retained legacy builder's
neutralization (--record); nothing else is removed, and nothing is removed unless
every target matches its record. This is a composition recipe, not a general
deletion API or native executor installation.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

# Removal targets must sit below one of these parents, never be one of them.
PARENTS = ('/opt/', '/private/etc/', '/private/var/lib/', '/usr/local/libexec/', '/Library/LaunchDaemons/')


def recorded_targets(record):
    """Return {absolute path: inventory} from the legacy builder's neutralization record."""
    targets = json.loads(Path(record).read_text())['neutralization']['removed_inventories']
    if not isinstance(targets, dict) or not targets:
        raise ValueError('The record lists no inventoried targets')
    for name, expected in targets.items():
        if (not isinstance(name, str) or os.path.normpath(name) != name or not name.startswith(PARENTS)
                or name.rstrip('/') + '/' in PARENTS or not isinstance(expected, dict)
                or set(expected) != {'entries', 'file_bytes', 'inventory_sha256'}):
            raise ValueError(f'Unexpected recorded target: {name!r}')
    return targets


def inventory(root):
    items = [root]
    if root.is_dir() and not root.is_symlink():
        items += sorted(root.rglob('*'))
    records = []
    for path in items:
        stat = path.lstat()
        record = {'path': str(path), 'mode': stat.st_mode, 'bytes': stat.st_size}
        if path.is_symlink():
            record['symlink'] = os.readlink(path)
        elif path.is_file():
            with path.open('rb') as stream:
                record['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        records.append(record)
    raw = json.dumps(records, sort_keys=True, separators=(',', ':')).encode()
    return {'entries': len(records), 'inventory_sha256': hashlib.sha256(raw).hexdigest(),
            'file_bytes': sum(r['bytes'] for r in records if 'sha256' in r)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True,
                        help='the dated native-base provenance record of the retained legacy builder')
    args = parser.parse_args()
    targets = recorded_targets(args.record)
    assert os.geteuid() == 0
    assert subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model']).decode().strip().startswith('VirtualMac')
    assert os.environ.get('AI_IMAGE_LAYER') == 'macos-xcode-maestro'
    receipt = Path('/opt/ai-runner-images/base-receipt.json')
    assert not receipt.exists(), 'Reconcile existing recipe result'
    users = subprocess.check_output(['/usr/bin/dscl', '.', '-list', '/Users', 'UniqueID']).decode()
    assert not [line for line in users.splitlines() if int(line.split()[-1]) >= 500]
    assert not Path('/private/etc/kcpassword').exists()
    state = Path('/private/var/lib/macos-tart')
    assert not state.exists() or not list(state.iterdir())
    required = [
        '/opt/macos-tart-bootstrap/resolver-tools/java-17.0.20.1+1/jdk-17.0.20.1+1/Contents/Home/bin/java',
        '/opt/macos-tart-bootstrap/resolver-tools/maestro-2.10.0/maestro/bin/maestro',
        '/opt/macos-tart-bootstrap/resolver-tools/node-22.23.2/node-v22.23.2-darwin-arm64/bin/node',
        '/opt/macos-tart-bootstrap/python/bin/python3.12',
        '/opt/macos-tart-bootstrap/public-tools/Xcode_26.5-runner.app/Contents/Developer/usr/bin/xcodebuild',
        '/opt/macos-tart-guest-agent/bin/tart-guest-agent',
    ]
    assert not any(item == name or item.startswith(name + '/') for name in targets
                   for item in [*required, str(receipt.parent)]), 'A recorded target holds a preserved path'
    preserved = {}
    for name in required:
        path = Path(name)
        assert path.is_file() and os.access(path, os.X_OK), name
        with path.open('rb') as stream:
            preserved[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    # This copy must be the recorded legacy builder: every target present, unchanged
    # and reached without a symlinked parent, before anything is removed.
    before = {}
    for name, expected in sorted(targets.items()):
        path = Path(name)
        assert os.path.lexists(name) and os.path.realpath(path.parent) == str(path.parent), name
        before[name] = inventory(path)
        assert before[name] == expected, f'{name} differs from the record'
    receipt.parent.mkdir(mode=0o755, exist_ok=True)
    receipt.parent.chmod(0o755)
    (receipt.parent / 'neutralization-intent.json').write_text(json.dumps(before, indent=2) + '\n')
    for name in sorted(targets):
        path = Path(name)
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    assert not any(os.path.lexists(name) for name in targets)
    tool_root = '/opt/macos-tart-bootstrap/resolver-tools'
    paths = {
        'java_home': tool_root + '/java-17.0.20.1+1/jdk-17.0.20.1+1/Contents/Home',
        'maestro': tool_root + '/maestro-2.10.0/maestro/bin/maestro',
        'node_bin': tool_root + '/node-22.23.2/node-v22.23.2-darwin-arm64/bin',
        'python': '/opt/macos-tart-bootstrap/python/bin/python3.12',
        'developer_dir': '/opt/macos-tart-bootstrap/public-tools/Xcode_26.5-runner.app/Contents/Developer',
    }
    bin_dir = receipt.parent / 'bin'
    bin_dir.mkdir(mode=0o755, exist_ok=True)
    bin_dir.chmod(0o755)
    maestro = bin_dir / 'maestro'
    maestro.write_text('#!/bin/sh\nexport JAVA_HOME=' + paths['java_home'] + '\nexec ' + paths['maestro'] + ' "$@"\n')
    maestro.chmod(0o755)
    for name, target in [('node', paths['node_bin'] + '/node'), ('npm', paths['node_bin'] + '/npm'), ('python3', paths['python'])]:
        (bin_dir / name).symlink_to(target)
    Path('/etc/paths.d/ai-runner-tools').write_text(str(bin_dir) + '\n')
    (receipt.parent / 'toolchain-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
    result = {'schema_version': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'removed': before, 'inventoried_agent_and_consumer_paths_removed': True,
              'preserved_executables': preserved,
              'ordinary_accounts_present': False, 'credential_material_delivered': False,
              'toolchain_paths': paths, 'runtime_admission': False}
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
