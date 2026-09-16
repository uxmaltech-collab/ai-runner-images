#!/usr/bin/env python3
"""Resolve locked owner modules from an existing checkout without network access."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-checkout', type=Path, required=True)
    parser.add_argument('--source-kind', choices=('templates', 'consumer'), default='templates')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--git', default=shutil.which('git'))
    args = parser.parse_args()
    recipe = Path(__file__).resolve().parent
    lock = json.loads((recipe / 'module-lock.json').read_bytes())
    source = lock['upstream_owner' if args.source_kind == 'templates' else 'verified_consumer']
    if not args.git or args.output.exists() or args.output.is_symlink():
        raise RuntimeError('Git is required and the output must be a new directory')
    root = args.source_checkout.resolve(strict=True)
    files = {}
    for name, record in lock['modules'].items():
        if name == lock['package_marker']['name']:
            raw = b''
        else:
            command = [args.git, '-c', 'core.hooksPath=/dev/null', '-c', 'protocol.allow=never',
                '-C', str(root), 'show', source['commit'] + ':' + lock['prefix'] + name]
            result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                check=True, timeout=15, env={**os.environ, 'GIT_NO_REPLACE_OBJECTS': '1',
                                           'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'})
            raw = result.stdout
        if len(raw) != record['bytes'] or sha(raw) != record['sha256']:
            raise RuntimeError('Locked module mismatch: ' + name)
        ast.parse(raw)
        files['lib/runner_control_plane/' + name] = raw
    helper = (recipe / 'qualification-session.py').read_bytes()
    provenance = json.loads((recipe / 'provenance.json').read_bytes())
    if sha(helper) != provenance['qualification_helper_sha256']:
        raise RuntimeError('Qualification adapter does not match its provenance')
    ast.parse(helper)
    files['qualification-session.py'] = helper
    files['MODULES.json'] = json_bytes({'schema_version': 1,
        'source_commit': lock['verified_consumer']['commit'],
        'source_repository': lock['verified_consumer']['repository'],
        'resolved_from': {'repository': source['repository'], 'commit': source['commit']},
        'upstream_owner': lock['upstream_owner'], 'modules': lock['modules']})
    # Verify every input before creating the output. Retain an incomplete output
    # for reconciliation if a later filesystem write fails; never replace it.
    args.output.mkdir(mode=0o700, parents=False)
    for name, raw in files.items():
        path = args.output / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(0o700 if name == 'qualification-session.py' else 0o600)
    manifest = {'schema_version': 1, 'qualification_only': True, 'network_calls': 0,
        'native_operations': 0, 'guest_destination': '/opt/ai-runner-qualification',
        'source_repository': source['repository'], 'source_commit': source['commit'],
        'lock_sha256': sha((recipe / 'module-lock.json').read_bytes()),
        'files': [{'name': name, 'bytes': len(raw), 'sha256': sha(raw),
                   'guest_mode': '0755' if name == 'qualification-session.py' else '0644'}
                  for name, raw in sorted(files.items())]}
    raw = json_bytes(manifest)
    with (args.output / 'PAYLOAD-MANIFEST.json').open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'manifest': str(args.output / 'PAYLOAD-MANIFEST.json'),
                      'bytes': len(raw), 'sha256': sha(raw)}))


if __name__ == '__main__':
    main()
