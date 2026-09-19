#!/usr/bin/env python3
"""Run real, positive and negative SwiftLint fixtures as the disposable GUI user."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import xml.etree.ElementTree as ET

RECIPE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    identity = pwd.getpwuid(os.getuid())
    membership = subprocess.run(['/usr/bin/dsmemberutil', 'checkmembership', '-U', identity.pw_name,
                                 '-G', 'admin'], capture_output=True, text=True, timeout=10)
    if os.getuid() == 0 or identity.pw_dir != os.environ.get('HOME'):
        raise ValueError('A real non-root account and matching HOME are required')
    if membership.returncode != 0 or 'is not a member' not in membership.stdout:
        raise ValueError('The fixture must run as a nonadministrator')
    if not args.output.is_relative_to(Path(identity.pw_dir)):
        raise ValueError('Fixture output must be inside the disposable user home')
    args.output.mkdir(mode=0o700)  # New attempt; never replace earlier evidence.
    receipt = {'schema_version': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'uid': os.getuid(), 'gid': os.getgid(), 'user': identity.pw_name,
               'home': identity.pw_dir, 'admin': False, 'path': os.environ['PATH'], 'commands': [],
               'status': 'started', 'app_build_or_canary': False}
    target = args.output / 'result.json'
    def save():
        target.write_text(json.dumps(receipt, indent=2) + '\n')
    try:
        launcher = shutil.which('swiftlint')
        if launcher is None:
            raise ValueError('SwiftLint is absent from the declared runtime PATH')
        receipt['launcher'] = {'path': launcher, 'sha256': hashlib.sha256(Path(launcher).read_bytes()).hexdigest()}
        save()
        for name in ('Valid.swift', 'Invalid.swift', 'swiftlint.yml'):
            shutil.copyfile(RECIPE / 'fixtures' / name, args.output / name)
        version = subprocess.check_output([launcher, 'version'], text=True, timeout=20).strip()
        if version != '0.65.1':
            raise ValueError(f'Unexpected SwiftLint version: {version}')
        receipt['version'] = version
        for fixture, valid in [('Valid.swift', True), ('Invalid.swift', False)]:
            command = [launcher, 'lint', '--strict', '--no-cache', '--config', 'swiftlint.yml',
                       '--reporter', 'junit', fixture]
            record = {'argv': command, 'fixture': fixture, 'expected_valid': valid}
            receipt['commands'].append(record)
            save()
            try:
                process = subprocess.run(command, cwd=args.output, capture_output=True, timeout=90)
            except subprocess.TimeoutExpired as error:
                (args.output / (fixture + '.partial.stdout')).write_bytes(error.stdout or b'')
                (args.output / (fixture + '.partial.stderr')).write_bytes(error.stderr or b'')
                record['timeout_seconds'] = 90
                raise
            junit = args.output / (fixture + '.junit.xml')
            junit.write_bytes(process.stdout)
            (args.output / (fixture + '.stderr')).write_bytes(process.stderr)
            root = ET.fromstring(process.stdout)
            failures = root.findall('.//failure') + root.findall('.//error')
            record.update(exit_code=process.returncode, failures=len(failures),
                          junit_sha256=hashlib.sha256(process.stdout).hexdigest())
            if valid:
                assert process.returncode == 0 and not failures, record
            else:
                assert process.returncode != 0 and failures and b'force_cast' in process.stdout, record
        receipt['status'] = 'passed'
    except BaseException as error:
        receipt.update(status='failed', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        save()
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
