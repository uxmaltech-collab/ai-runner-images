#!/usr/bin/env python3
"""Check all agent versions as the guest job user with an empty auth-free home."""
import argparse
import datetime
import grp
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import tempfile

PREFIX = Path('/opt/ai-runner-images/agents')


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.geteuid() == 0:
        raise ValueError('Run as the intended nonadministrator user in the macOS arm64 builder guest.')
    if grp.getgrnam('admin').gr_gid in os.getgroups():
        raise ValueError('The qualification account must not belong to the administrator group.')
    if args.receipt.exists():
        raise ValueError('Receipt already exists; do not overwrite qualification evidence.')
    pins_raw = (PREFIX / 'pins.json').read_bytes()
    pins = json.loads(pins_raw)
    payloads = []
    for relative, pin in [('codex/codex', pins['codex']['binary']),
            ('codex/codex-code-mode-host', pins['codex']['companion']),
            ('claude/claude', pins['claude']), ('grok/grok', pins['grok'])]:
        path = PREFIX / relative
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if path.stat().st_size != pin['bytes'] or digest.hexdigest() != pin['sha256']:
            raise ValueError(f'Installed agent payload differs from lock: {relative}')
        payloads.append({'path': str(path), 'bytes': pin['bytes'], 'sha256': pin['sha256']})
    checks = []
    with tempfile.TemporaryDirectory(prefix='agent-version-check-') as home:
        env = {'PATH': str(PREFIX / 'bin') + ':/usr/bin:/bin:/usr/sbin:/sbin',
            'HOME': home, 'CODEX_HOME': str(Path(home) / 'codex'),
            'DISABLE_AUTOUPDATER': '1', 'LANG': 'en_US.UTF-8', 'CI': '1'}
        for engine in ('codex', 'claude', 'grok'):
            command = [str(PREFIX / 'bin' / engine), '--version']
            process = subprocess.Popen(command, env=env, cwd=home, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            timed_out = False
            try:
                stdout, stderr = process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            text = stdout.decode('utf-8', errors='replace').strip()
            checks.append({'engine': engine, 'command': command, 'returncode': process.returncode,
                'stdout': text, 'stderr': stderr.decode('utf-8', errors='replace').strip(),
                'timed_out': timed_out, 'expected_version': pins[engine]['version'],
                'passed': process.returncode == 0 and not timed_out and bool(re.search(
                    r'(?<![0-9])' + re.escape(pins[engine]['version']) + r'(?![0-9])', text))})
    receipt = {'schema_version': 1, 'operation': 'native-agent-layer-auth-free-version-check',
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'uid': os.getuid(),
        'gid': os.getgid(), 'pins_sha256': hashlib.sha256(pins_raw).hexdigest(),
        'checks': checks, 'passed': all(row['passed'] for row in checks),
        'installed_payloads': payloads,
        'temporary_home_removed': True, 'agent_authentication_attempted': False,
        'scope': 'All three native CLIs start and report their pinned versions; model authentication and an agent task are separate job-time operations.'}
    with args.receipt.open('x') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'passed': receipt['passed'], 'receipt': str(args.receipt)}, sort_keys=True))
    raise SystemExit(0 if receipt['passed'] else 1)


if __name__ == '__main__':
    main()
