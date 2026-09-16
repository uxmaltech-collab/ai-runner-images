#!/usr/bin/env python3
"""Correct only the two public directories affected by the builder umask.

Run inside a new accountless copy. Preserve the previous sealed artifact.
"""
import json
import os
from pathlib import Path
import stat
import subprocess

assert os.getuid() == 0
assert subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model']).decode().startswith('VirtualMac')
users = subprocess.check_output(['/usr/bin/dscl', '.', '-list', '/Users', 'UniqueID'], text=True)
assert not [row for row in users.splitlines() if int(row.split()[-1]) >= 500]
receipt = Path('/opt/ai-runner-images/public-directory-repair.json')
assert not receipt.exists()
records = []
for path in [Path('/opt/ai-runner-images'), Path('/opt/ai-runner-images/bin')]:
    before = path.lstat()
    assert stat.S_ISDIR(before.st_mode) and before.st_uid == 0
    assert stat.S_IMODE(before.st_mode) in (0o700, 0o755)
    path.chmod(0o755)
    assert stat.S_IMODE(path.stat().st_mode) == 0o755
    records.append({'path': str(path), 'before': oct(stat.S_IMODE(before.st_mode)), 'after': '0o755'})
result = {'operation': 'repair-public-tool-directory-traversal', 'directories': records,
          'accounts_created': False, 'files_or_credentials_changed': False}
receipt.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
