#!/usr/bin/env python3
"""Install and precache a pinned Flutter SDK inside an authorized builder guest."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import zipfile

RECIPE = Path(__file__).resolve().parent
PREFIX = Path('/opt/ai-runner-images/flutter')


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def inspect_archive(path, pins):
    pin = pins['archive']
    if path.stat().st_size != pin['bytes'] or sha_file(path) != pin['sha256']:
        raise ValueError('Flutter archive bytes differ from the official release pin.')
    expanded, links, names = 0, 0, set()
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            name = entry.filename.rstrip('/')
            parts = PurePosixPath(name).parts
            mode = entry.external_attr >> 16
            if not parts or parts[0] != 'flutter' or '..' in parts or '\\' in name or name in names:
                raise ValueError('Unexpected or duplicate archive path.')
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK) or mode & 0o6000:
                raise ValueError('Unsupported archive entry type or permissions.')
            names.add(name)
            expanded += entry.file_size
            if len(names) > 100000 or expanded > 8 * 1024 ** 3:
                raise ValueError('Archive expansion exceeds the bounded SDK installation.')
            if stat.S_ISLNK(mode):
                links += 1
                if entry.file_size > 4096:
                    raise ValueError('Oversize SDK symlink.')
                target = archive.read(entry).decode('utf-8')
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                if target.startswith('/') or not resolved.startswith('flutter/'):
                    raise ValueError('SDK symlink escapes the extracted tree.')
        version = json.loads(archive.read('flutter/bin/cache/flutter.version.json'))
        if version['frameworkRevision'] != pins['flutter_revision'] or version['dartSdkVersion'] != pins['dart_version']:
            raise ValueError('Archive framework or Dart revision differs from the pin.')
    return {'archive_bytes': pin['bytes'], 'archive_sha256': pin['sha256'],
        'members': len(names), 'expanded_bytes': expanded, 'symlinks': links,
        'flutter_revision': pins['flutter_revision'], 'dart_version': pins['dart_version']}


def run(command, environment, cwd, log, timeout, separate_stderr=False):
    error_path = log.with_suffix('.stderr.log') if separate_stderr else None
    error_stream = error_path.open('xb') if error_path else None
    try:
        with log.open('xb') as stream:
            process = subprocess.Popen(command, env=environment, cwd=cwd,
                stdin=subprocess.DEVNULL, stdout=stream,
                stderr=error_stream if error_stream else subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise RuntimeError(f'Command timed out; original log preserved at {log}')
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if error_stream:
            error_stream.flush()
            os.fsync(error_stream.fileno())
            error_stream.close()
    if code:
        raise RuntimeError(f'Command returned {code}; original log preserved at {log}')
    receipt = {'argv': command, 'returncode': code, 'log': str(log),
        'log_bytes': log.stat().st_size, 'log_sha256': sha_file(log)}
    if error_path:
        receipt.update(stderr_log=str(error_path), stderr_bytes=error_path.stat().st_size,
            stderr_sha256=sha_file(error_path))
    return receipt


def inventory_and_seal(root):
    entries = []
    for directory, subdirs, filenames in os.walk(root, followlinks=False):
        for name in sorted(subdirs + filenames):
            path = Path(directory) / name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                entries.append({'path': relative, 'kind': 'symlink', 'target': os.readlink(path)})
                os.lchown(path, 0, 0)
            elif stat.S_ISDIR(info.st_mode):
                path.chmod(0o555)
                os.chown(path, 0, 0)
                entries.append({'path': relative, 'kind': 'directory'})
            elif stat.S_ISREG(info.st_mode):
                mode = 0o555 if info.st_mode & 0o111 else 0o444
                path.chmod(mode)
                os.chown(path, 0, 0)
                entries.append({'path': relative, 'kind': 'file', 'bytes': info.st_size,
                    'mode': mode, 'sha256': sha_file(path)})
            else:
                raise ValueError(f'Unexpected SDK file type: {relative}')
    root.chmod(0o555)
    os.chown(root, 0, 0)
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--runtime-python', type=Path, default=Path(sys.executable))
    parser.add_argument('--inspect-only', action='store_true')
    args = parser.parse_args()
    pins_raw = (RECIPE / 'pins.json').read_bytes()
    pins = json.loads(pins_raw)
    inspection = inspect_archive(args.archive, pins)
    args.evidence_dir.mkdir(mode=0o700)
    write_json(args.evidence_dir / 'ARCHIVE-VERIFICATION.json', inspection)
    if args.inspect_only:
        print(json.dumps(inspection, sort_keys=True))
        return
    if platform.system() != 'Darwin' or platform.machine() != 'arm64' or os.geteuid() != 0:
        raise ValueError('Install inside the declared macOS arm64 builder guest as root.')
    if PREFIX.exists() or PREFIX.is_symlink():
        raise ValueError('Preserve the existing Flutter layer and reconcile its receipt.')
    if not args.runtime_python.is_absolute() or not args.runtime_python.is_file():
        raise ValueError('Provide the permanent Python interpreter supplied by the base image.')
    runtime_python = args.runtime_python.resolve(strict=True)
    parent_pins = json.loads(Path('/opt/ai-runner-images/agents/pins.json').read_bytes())
    if set(parent_pins['engines']) != {'codex', 'claude', 'grok'}:
        raise ValueError('Flutter must inherit the complete three-agent layer.')
    for ancestor in (PREFIX.parent, *PREFIX.parent.parents):
        info = ancestor.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError(f'Unprotected SDK installation parent: {ancestor}')
    if shutil.disk_usage(PREFIX.parent).free < inspection['expanded_bytes'] + 2 * 1024 ** 3:
        raise ValueError('Insufficient free bytes for the SDK and bounded precache workspace.')
    stage = Path(tempfile.mkdtemp(prefix='.flutter-incoming-', dir=PREFIX.parent))
    stage.chmod(0o755)
    version_root = stage / pins['flutter_version']
    version_root.mkdir(mode=0o755)
    home = args.evidence_dir / 'temporary-home'
    home.mkdir(mode=0o700)
    cache = version_root / 'pub-cache-seed'
    cache.mkdir(mode=0o755)
    environment = {'HOME': str(home), 'PATH': '/opt/ai-runner-images/agents/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
        'PUB_CACHE': str(cache), 'CI': 'true', 'FLUTTER_SUPPRESS_ANALYTICS': 'true',
        'DART_SUPPRESS_ANALYTICS': 'true', 'LANG': 'en_US.UTF-8'}
    commands = []
    commands.append(run(['/usr/bin/ditto', '-x', '-k', str(args.archive), str(version_root)],
        environment, stage, args.evidence_dir / 'extract.log', 600))
    sdk = version_root / 'sdk'
    os.rename(version_root / 'flutter', sdk)
    flutter = str(sdk / 'bin/flutter')
    dart = str(sdk / 'bin/dart')
    for label, argv, timeout in [
        ('flutter-analytics', [flutter, '--suppress-analytics', '--disable-analytics'], 120),
        ('dart-analytics', [dart, '--disable-analytics'], 120),
        ('precache-ios', [flutter, '--suppress-analytics', 'precache', '--ios'], 1200),
        ('flutter-version', [flutter, '--suppress-analytics', '--version', '--machine'], 120),
        ('dart-version', [dart, '--version'], 120),
    ]:
        commands.append(run(argv, environment, sdk, args.evidence_dir / (label + '.log'), timeout,
            separate_stderr=label == 'flutter-version'))
    version = json.loads((args.evidence_dir / 'flutter-version.log').read_text())
    if version['frameworkRevision'] != pins['flutter_revision'] or version['dartSdkVersion'] != pins['dart_version']:
        raise ValueError('Executed framework or Dart version differs from the release pin.')
    sdk_manifest = inventory_and_seal(sdk)
    pub_manifest = inventory_and_seal(cache)
    write_json(version_root / 'SDK-MANIFEST.json', {'sdk': sdk_manifest, 'pub_cache_seed': pub_manifest})
    write_json(version_root / 'SDK-READY.json', {'schema_version': 1,
        'status': 'precache-complete-and-sealed', 'flutter_version': pins['flutter_version'],
        'flutter_revision': pins['flutter_revision'], 'dart_version': pins['dart_version'],
        'archive_sha256': pins['archive']['sha256'], 'manifest_sha256': sha_file(version_root / 'SDK-MANIFEST.json'),
        'precache_platforms': ['ios'], 'agent_engines_in_parent': parent_pins['engines']})
    (stage / 'pins.json').write_bytes(pins_raw)
    shutil.copyfile(RECIPE / 'launcher.py', stage / 'launcher.py')
    (stage / 'bin').mkdir(mode=0o755)
    for tool in ('flutter', 'dart'):
        wrapper = '#!/bin/sh\nexec ' + shlex.quote(str(runtime_python)) + ' ' + shlex.quote(str(PREFIX / 'launcher.py')) + ' ' + tool + ' "$@"\n'
        (stage / 'bin' / tool).write_text(wrapper)
        (stage / 'bin' / tool).chmod(0o555)
    for path in (stage / 'pins.json', stage / 'launcher.py', version_root / 'SDK-MANIFEST.json', version_root / 'SDK-READY.json'):
        path.chmod(0o444)
    for path in (stage, version_root, stage / 'bin'):
        path.chmod(0o555)
    os.rename(stage, PREFIX)
    shutil.rmtree(home)
    receipt = {'schema_version': 1, 'status': 'installed-and-precached',
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'archive': inspection,
        'commands': commands, 'prefix': str(PREFIX), 'runtime_python': str(runtime_python),
        'sdk_ready_sha256': sha_file(PREFIX / pins['flutter_version'] / 'SDK-READY.json'),
        'sdk_manifest_sha256': sha_file(PREFIX / pins['flutter_version'] / 'SDK-MANIFEST.json'),
        'accounts_created': 0, 'temporary_home_removed': True,
        'nonadministrator_qualification': 'pending-in-disposable-qualification-clone'}
    write_json(args.evidence_dir / 'INSTALLATION-RECEIPT.json', receipt)
    print(json.dumps({'status': receipt['status'], 'receipt': str(args.evidence_dir / 'INSTALLATION-RECEIPT.json')}, sort_keys=True))


if __name__ == '__main__':
    main()
