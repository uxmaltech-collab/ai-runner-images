#!/usr/bin/env python3
"""Install all three pinned agents into a new builder guest layer, without auth.

The versions and digests are the consumer's adopted collab.harness-pins/v2
document; this recipe carries none of its own.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import tempfile

PREFIX = Path('/opt/ai-runner-images/agents')
# The document's name beside this recipe in the guest payload and in the
# installed tree, where it is the receipt copy of the pins installed from.
PINS_NAME = 'harness-pins.yaml'
SCHEMA = 'collab.harness-pins/v2'
PLATFORM = 'darwin-arm64'
ENGINES = ('codex', 'claude', 'grok')
_ENTRY = re.compile(r'(?P<indent> *)(?P<key>[A-Za-z0-9][A-Za-z0-9_.-]*):'
                    r'(?: +(?P<value>"[^"\\]*"|\'[^\']*\'|[A-Za-z0-9][A-Za-z0-9._/+-]*))?(?: +#.*)?')
_VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')
_DIGEST = re.compile(r'[0-9a-f]{64}')
_PLATFORM = re.compile(r'(?:linux|darwin)-(?:amd64|arm64)')
_COMPANION = re.compile(r'[a-z][a-z0-9-]{0,62}')


def parse_pins(text):
    """Read the block-mapping YAML the harness pins are written in; refuse anything else."""
    root = {}
    stack = [[0, root]]
    opened = False
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip(' ').startswith('#'):
            continue
        match = _ENTRY.fullmatch(line)
        if not match:
            raise ValueError(f'Harness pins line {number} is not a plain block-mapping entry')
        indent = len(match['indent'])
        if opened:
            if indent <= stack[-2][0]:
                raise ValueError(f'Harness pins line {number} follows a key without a value')
            stack[-1][0] = indent
            opened = False
        else:
            while indent < stack[-1][0]:
                stack.pop()
            if indent != stack[-1][0]:
                raise ValueError(f'Harness pins line {number} has inconsistent indentation')
        mapping, key, value = stack[-1][1], match['key'], match['value']
        if key in mapping:
            raise ValueError(f'Harness pins line {number} repeats key {key}')
        if value is None:
            mapping[key] = {}
            stack.append([None, mapping[key]])
            opened = True
        else:
            mapping[key] = value[1:-1] if value[0] in '"\'' else value
    if opened:
        raise ValueError('Harness pins end with a key without a value')
    return root


def _digests(value, label):
    if (not isinstance(value, dict) or not value or not all(isinstance(key, str) and _PLATFORM.fullmatch(key)
            and isinstance(digest, str) and _DIGEST.fullmatch(digest) for key, digest in value.items())):
        raise ValueError(f'Harness pins carry malformed digests for {label}')
    return value


def native_pins(document, source='harness pins'):
    """Return this layer's versions and darwin-arm64 executable digests, by installed path."""
    found = document.get('schema') if isinstance(document, dict) else None
    if found != SCHEMA:
        raise ValueError(f'{source} is not a {SCHEMA} document (schema: {found!r})')
    harnesses = document.get('harnesses')
    if set(document) != {'schema', 'harnesses'} or not isinstance(harnesses, dict) or set(harnesses) != set(ENGINES):
        raise ValueError(f'{source} must declare exactly the harnesses {sorted(ENGINES)}')
    for name, harness in harnesses.items():
        if (not isinstance(harness, dict) or set(harness) - {'version', 'sha256', 'companions'}
                or not isinstance(harness.get('version'), str) or not _VERSION.fullmatch(harness['version'])):
            raise ValueError(f'{source} declares no exact version of {name}')
        if 'sha256' in harness:
            _digests(harness['sha256'], name)
        companions = harness.get('companions', {})
        if not isinstance(companions, dict) or ('companions' in harness and not companions):
            raise ValueError(f'{source} carries malformed companions of {name}')
        for companion, digests in companions.items():
            if not _COMPANION.fullmatch(companion):
                raise ValueError(f'{source} names an invalid companion of {name}')
            _digests(digests, f'{name} {companion}')
    if not {'linux-amd64', 'linux-arm64'} <= set(harnesses['grok'].get('sha256', {})):
        raise ValueError(f'{source} lacks the Linux digests of grok')
    files = {}
    for target, harness, digests in [
            ('codex/codex', 'codex', harnesses['codex'].get('sha256', {})),
            ('codex/codex-code-mode-host', 'the codex companion codex-code-mode-host',
             harnesses['codex'].get('companions', {}).get('codex-code-mode-host', {})),
            ('claude/claude', 'claude', harnesses['claude'].get('sha256', {})),
            ('grok/grok', 'grok', harnesses['grok'].get('sha256', {}))]:
        if PLATFORM not in digests:
            raise ValueError(f'{source} lacks the {PLATFORM} digest of {harness}')
        files[target] = digests[PLATFORM]
    return {'versions': {name: harnesses[name]['version'] for name in ENGINES}, 'files': files}


def read_pins(path):
    """Return the exact bytes of a harness pins document and its native pins."""
    raw = Path(path).read_bytes()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError(f'{path} is not UTF-8 harness pins') from error
    return raw, native_pins(parse_pins(text), str(path))


def input_names(pins):
    """Offline input file names: the vendors' versioned executable names."""
    versions = pins['versions']
    return {'codex/codex': 'codex', 'codex/codex-code-mode-host': 'codex-code-mode-host',
            'claude/claude': f"claude-{versions['claude']}-darwin-arm64",
            'grok/grok': f"grok-{versions['grok']}-macos-aarch64"}


def vendor_sources(pins):
    """Where each pinned executable is published; the Codex digests are of the archived executables."""
    versions = pins['versions']
    release = f"https://github.com/openai/codex/releases/download/rust-v{versions['codex']}/"
    return {'codex/codex': release + 'codex-aarch64-apple-darwin.tar.gz',
            'codex/codex-code-mode-host': release + 'codex-code-mode-host-aarch64-apple-darwin.tar.gz',
            'claude/claude': f"https://downloads.claude.ai/claude-code-releases/{versions['claude']}/darwin-arm64/claude",
            'grok/grok': f"https://x.ai/cli/grok-{versions['grok']}-macos-aarch64"}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def verify(path, sha256):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f'Unexpected payload type: {path}')
    if digest(path) != sha256:
        raise ValueError(f'Payload digest mismatch: {path}')


def launcher_bytes(engine, prefix=PREFIX):
    wrapper = '#!/bin/sh\n'
    if engine == 'claude':
        wrapper += 'export DISABLE_AUTOUPDATER=1\n'
    wrapper += f'exec {prefix}/{engine}/{engine} "$@"\n'
    return wrapper.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--harness-pins', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, required=True)
    parser.add_argument('--codex-binary', type=Path, required=True)
    parser.add_argument('--codex-companion', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--verify-inputs-only', action='store_true')
    args = parser.parse_args()
    pins_raw, pins = read_pins(args.harness_pins)
    names, sources = input_names(pins), vendor_sources(pins)
    entries = [
        ('codex/codex', args.codex_binary),
        ('codex/codex-code-mode-host', args.codex_companion),
        ('claude/claude', args.artifacts / names['claude/claude']),
        ('grok/grok', args.artifacts / names['grok/grok']),
    ]
    if args.receipt.exists():
        raise ValueError('Receipt already exists; reconcile the completed or partial operation.')
    for target, source in entries:
        verify(source, pins['files'][target])
    receipt = {'schema_version': 2, 'operation': 'native-agent-layer-input-verification',
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'engines': list(ENGINES), 'versions': pins['versions'], 'harness_pins_schema': SCHEMA,
        'harness_pins_sha256': hashlib.sha256(pins_raw).hexdigest(),
        'installed': False, 'binary_execution': False, 'network_calls': 0,
        'source_files': [{'path': str(source), 'destination': str(PREFIX / target),
            'bytes': source.stat().st_size, 'sha256': pins['files'][target],
            'vendor_source': sources[target]} for target, source in entries]}
    if not args.verify_inputs_only:
        if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.geteuid() != 0:
            raise ValueError('Installation runs as root inside the declared macOS arm64 builder guest.')
        if PREFIX.exists() or PREFIX.is_symlink():
            raise ValueError('Agent layer already exists; preserve it and reconcile its receipt.')
        if not PREFIX.parent.exists():
            PREFIX.parent.mkdir(mode=0o755)
            PREFIX.parent.chmod(0o755)
        for parent in (PREFIX.parent, *PREFIX.parent.parents):
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError(f'Unprotected installation parent: {parent}')
        stage = Path(tempfile.mkdtemp(prefix='.agents-incoming-', dir=PREFIX.parent))
        # Leave the staging directory on error for inspection; never erase an older layer.
        stage.chmod(0o755)
        for target, source in entries:
            destination = stage / target
            destination.parent.mkdir(mode=0o755, exist_ok=True)
            destination.parent.chmod(0o755)
            shutil.copyfile(source, destination)
            verify(destination, pins['files'][target])
            destination.chmod(0o755)
        (stage / 'bin').mkdir(mode=0o755)
        (stage / 'bin').chmod(0o755)
        for engine in ENGINES:
            (stage / 'bin' / engine).write_bytes(launcher_bytes(engine))
            (stage / 'bin' / engine).chmod(0o755)
        (stage / PINS_NAME).write_bytes(pins_raw)
        (stage / PINS_NAME).chmod(0o644)
        os.rename(stage, PREFIX)
        receipt.update(operation='native-agent-layer-installation', installed=True,
            prefix=str(PREFIX), runtime_path=str(PREFIX / 'bin'),
            configuration_or_credentials_created=False)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x') as stream:
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'installed': receipt['installed'], 'engines': list(ENGINES),
        'receipt': str(args.receipt), 'receipt_sha256': digest(args.receipt)}, sort_keys=True))


if __name__ == '__main__':
    main()
