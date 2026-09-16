#!/usr/bin/env python3
"""Remove inventoried consumer/agent material from a new accountless builder copy.

The parent is preserved by the host COW operation. This is a composition recipe,
not a general deletion API or native executor installation.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

TARGETS = [
    '/opt/macos-tart-bootstrap/resolver-tools/codex-0.151.0',
    '/opt/ai-repo-resources', '/opt/macos-tart-guest', '/opt/macos-tart-journey.json',
    '/private/etc/macos-tart-guest.json', '/usr/local/libexec/macos-tart-guest',
    '/private/var/lib/macos-tart-image-build',
    '/opt/macos-tart-bootstrap/native-completion-20260914-01',
    '/opt/macos-tart-bootstrap/native-closure-20260914-01',
    '/opt/macos-tart-bootstrap/native-recovery-20260914-01',
    '/Library/LaunchDaemons/org.macos-tart.rehearsal.firstboot-probe.plist',
]


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
    codex = Path(TARGETS[0]) / 'codex-aarch64-apple-darwin'
    with codex.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == '98491713ffb196061003ee148636e743997cc31d76144ba7c53462269896891d'
    before = {name: inventory(Path(name)) for name in TARGETS if Path(name).exists()}
    receipt.parent.mkdir(mode=0o755, exist_ok=True)
    (receipt.parent / 'neutralization-intent.json').write_text(json.dumps(before, indent=2) + '\n')
    for name in TARGETS:
        path = Path(name)
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    assert not any(os.path.lexists(name) for name in TARGETS)
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
    maestro = bin_dir / 'maestro'
    maestro.write_text('#!/bin/sh\nexport JAVA_HOME=' + paths['java_home'] + '\nexec ' + paths['maestro'] + ' "$@"\n')
    maestro.chmod(0o755)
    for name, target in [('node', paths['node_bin'] + '/node'), ('npm', paths['node_bin'] + '/npm'), ('python3', paths['python'])]:
        (bin_dir / name).symlink_to(target)
    Path('/etc/paths.d/ai-runner-tools').write_text(str(bin_dir) + '\n')
    (receipt.parent / 'toolchain-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
    result = {'schema_version': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'removed': before, 'agent_and_consumer_material_removed': True,
              'ordinary_accounts_present': False, 'credential_material_delivered': False,
              'toolchain_paths': paths, 'runtime_admission': False}
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
