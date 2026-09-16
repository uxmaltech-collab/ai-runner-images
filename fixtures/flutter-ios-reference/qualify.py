#!/usr/bin/env python3
"""Build and exercise the exact neutral fixture in a disposable nonadmin GUI.

Every subprocess is bounded and journaled. Only the simulator created by this
invocation may be shut down or deleted. This does not invoke an AI agent, create
a GitHub job, obtain credentials, or change a reusable image.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import grp
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import pwd
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

FIXTURE = {
    'pubspec.yaml': 'f991939abc182471f87609906588b28eb414ce74b3a94c01efc180fae4e9b489',
    'lib/main.dart': '60dd7b2c64d7aa0001d8fb23d85ac01257898e6084dd3af95473e04af981cefd',
    '.maestro/flows/hello-world.yaml': '92ef7de96458e5c4c1a43efb399ca7cc1ef6b9f094ae5c05001c7bc853ecfc64',
}
APP_ID = 'tech.uxmal.runnerHelloWorld'
AGENT_ENV = {'OPENAI_API_KEY', 'CODEX_API_KEY', 'RESOLVER_AUTH_JSON', 'ANTHROPIC_API_KEY',
             'CLAUDE_CODE_OAUTH_TOKEN', 'GROK_API_KEY', 'XAI_API_KEY'}
UUID = re.compile(r'[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}')


def need(value, reason):
    if not value:
        raise RuntimeError(reason)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def reference(path):
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}


def absent_group(pid):
    try:
        os.killpg(pid, 0)
        return False
    except ProcessLookupError:
        return True


class Run:
    def __init__(self, args, environment):
        self.args, self.environment = args, environment
        self.evidence = args.workdir / 'evidence'
        self.evidence.mkdir(mode=0o700)
        self.commands = self.evidence / 'commands'
        self.commands.mkdir(mode=0o700)
        self.end = time.monotonic() + args.max_seconds
        self.cancelled = False
        self.rows = []

    def interrupt(self, *_):
        self.cancelled = True

    def command(self, name, argv, *, timeout=60, cwd=None, check=True, cleanup=False):
        need(re.fullmatch(r'[a-z0-9-]+', name), 'invalid-command-name')
        record = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(cwd or self.args.workdir),
                  'started_at_utc': now(), 'timeout_seconds': timeout, 'exit_code': None,
                  'process_reaped': False, 'process_group_absent': False}
        write(self.commands / (name + '.intent.json'), record)
        output, process, failure = [bytearray(), bytearray()], None, None
        streams = [(self.commands / (name + '.' + suffix + '.log')).open('xb')
                   for suffix in ('stdout', 'stderr')]
        deadline = time.monotonic() + timeout
        if not cleanup:
            deadline = min(deadline, self.end)
        selector = selectors.DefaultSelector()
        try:
            need(cleanup or not self.cancelled, 'qualification-cancelled')
            need(time.monotonic() < deadline, 'qualification-deadline')
            process = subprocess.Popen(list(map(str, argv)), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=record['cwd'],
                env=self.environment, start_new_session=True, close_fds=True)
            record.update(pid=process.pid, process_group=process.pid)
            for index, stream in enumerate((process.stdout, process.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            counts = [0, 0]
            while selector.get_map() or process.poll() is None:
                need(cleanup or not self.cancelled, 'qualification-cancelled')
                need(time.monotonic() < deadline, 'command-timeout')
                for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                    block = os.read(key.fd, 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    streams[key.data].write(block)
                    counts[key.data] += len(block)
                    # Logs are streamed; only bounded command metadata is held.
                    if len(output[key.data]) < 12 * 1024**2:
                        output[key.data].extend(block[:12 * 1024**2 - len(output[key.data])])
                    need(sum(counts) <= 32 * 1024**2, 'command-output-limit')
            record['exit_code'] = process.returncode
            record['output_bytes'] = counts
        except BaseException as error:
            failure = error
            record['error_type'] = type(error).__name__
            record['reason'] = str(error) if isinstance(error, RuntimeError) else 'command-execution-error'
        finally:
            selector.close()
            if process is not None:
                # Kill only a remaining process group created by this command.
                # Even a successful parent may have left compiler descendants.
                if not absent_group(process.pid):
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        record['remaining_owned_group_killed'] = True
                    except ProcessLookupError:
                        pass
                try:
                    process.wait(timeout=5)
                    record['process_reaped'] = True
                    record['exit_code'] = process.returncode
                except subprocess.TimeoutExpired:
                    pass
                until = time.monotonic() + 5
                while not absent_group(process.pid) and time.monotonic() < until:
                    time.sleep(0.05)
                record['process_group_absent'] = absent_group(process.pid)
                for pipe in (process.stdout, process.stderr):
                    pipe.close()
            else:
                record['spawn_absent'] = True
            for stream in streams:
                stream.flush()
                os.fsync(stream.fileno())
                stream.close()
            record['finished_at_utc'] = now()
            record['logs'] = {suffix: reference(self.commands / (name + '.' + suffix + '.log'))
                              for suffix in ('stdout', 'stderr')}
            self.rows.append(record)
            write(self.commands / (name + '.receipt.json'), record)
        if failure is not None:
            raise failure
        need(record['process_reaped'] and record['process_group_absent'], 'command-cleanup-unconfirmed')
        need(not check or record['exit_code'] == 0, name + '-failed')
        return bytes(output[0]), record


def protected_fixture(root):
    need(root.is_absolute() and root.resolve(strict=True) == root, 'fixture-root-must-be-canonical')
    for directory in (*root.parents, root):
        info = directory.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
             'fixture-directory-not-protected')
    result = {}
    for name, expected in FIXTURE.items():
        path = root / name
        for directory in path.parents:
            if directory == root:
                break
            info = directory.lstat()
            need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                 'fixture-subdirectory-not-protected')
        info = path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
             and info.st_size <= 65536 and sha(path) == expected, 'fixture-file-mismatch')
        result[name] = reference(path)
    return result


def posix_groups():
    libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    libc.getgroups.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
    libc.getgroups.restype = ctypes.c_int
    count = libc.getgroups(0, None)
    need(0 <= count <= 1024, 'posix-group-count')
    values = (ctypes.c_uint * max(1, count))()
    observed = libc.getgroups(count, values)
    need(observed == count, 'posix-groups-raced')
    return list(values[:count])


def device_inventory(raw):
    value = json.loads(raw)
    return {row['udid'].upper(): row for rows in value.get('devices', {}).values() for row in rows}


def select_simulator(inventory):
    runtimes = [row for row in inventory['runtimes'] if row.get('isAvailable') is True
                and row['identifier'].startswith('com.apple.CoreSimulator.SimRuntime.iOS-')]
    need(runtimes, 'available-ios-runtime-required')
    key = lambda row: tuple(map(int, re.findall(r'\d+', row.get('version', '0'))))
    runtime = next((row for row in runtimes if row['identifier'] ==
                    'com.apple.CoreSimulator.SimRuntime.iOS-26-5'), max(runtimes, key=key))
    phones = [row for row in inventory['devicetypes'] if row.get('name', '').startswith('iPhone')]
    need(phones, 'iphone-device-type-required')
    phone = next((row for row in phones if row['name'] == 'iPhone 17'), phones[-1])
    return runtime, phone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('flutter', 'maestro', 'fixture-root', 'workdir', 'developer-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit')
    parser.add_argument('--image')
    parser.add_argument('--max-seconds', type=int, default=2400)
    args = parser.parse_args()
    need(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'darwin-arm64-required')
    account = pwd.getpwuid(os.getuid())
    need(os.getuid() == os.geteuid() != 0 and os.getgid() == os.getegid() != 0,
         'nonroot-real-effective-identity-required')
    groups = set(os.getgrouplist(account.pw_name, account.pw_gid))
    need(not groups.intersection({0, grp.getgrnam('admin').gr_gid}), 'nonadministrator-required')
    need(not AGENT_ENV.intersection(os.environ), 'agent-credential-environment-forbidden')
    need(not any((Path(account.pw_dir) / relative).exists() for relative in
                 ('.codex/auth.json', '.claude/.credentials.json')), 'agent-auth-file-present')
    need(os.environ.get('HOME') == account.pw_dir and args.workdir.is_absolute()
         and args.workdir.is_relative_to(Path(account.pw_dir))
         and args.workdir.parent.resolve(strict=True) == args.workdir.parent
         and args.workdir.parent.stat().st_uid == account.pw_uid
         and not os.path.lexists(args.workdir), 'fresh-owned-workdir-required')
    need(args.source_commit is None or re.fullmatch(r'[0-9a-f]{40}', args.source_commit), 'source-commit-format')
    need(300 <= args.max_seconds <= 7200, 'qualification-time-bound')
    fixtures = protected_fixture(args.fixture_root)
    for binary in (args.flutter, args.maestro):
        need(binary.is_absolute() and binary.is_file() and os.access(binary, os.X_OK), 'tool-executable-required')
    need(args.developer_dir.is_absolute() and args.developer_dir.is_dir(), 'xcode-directory-required')
    os.umask(0o077)
    args.workdir.mkdir(mode=0o700)
    environment = {name: os.environ[name] for name in ('PATH', 'HOME', 'USER', 'LOGNAME', 'JAVA_HOME',
                   'PUB_CACHE', 'FLUTTER_ROOT') if name in os.environ}
    environment.update(DEVELOPER_DIR=str(args.developer_dir), LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8',
        CI='true', FLUTTER_SUPPRESS_ANALYTICS='true', DART_SUPPRESS_ANALYTICS='true',
        MAESTRO_CLI_NO_ANALYTICS='1', MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED='true')
    run = Run(args, environment)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, run.interrupt)
    result = {'schema_version': 1, 'operation': 'flutter-ios-reference-qualification', 'started_at_utc': now(),
        'status': 'running', 'source_commit': args.source_commit, 'image': args.image,
        'fixture_files': fixtures, 'agent_invoked': False, 'agent_credentials_present': False,
        'input_tool_files': {name: {'path': str(path), **reference(path.resolve())} for name, path in
                             [('flutter', args.flutter), ('maestro', args.maestro)]},
        'warnings': [], 'cleanup': {}, 'simulator_udid': None}
    if args.source_commit is None:
        result['warnings'].append('Recipe commit was not supplied; exact fixture hashes remain recorded.')
    write(run.evidence / 'qualification-intent.json', result)
    simulator, create_attempted, screenshot_attempted = None, False, False
    xcrun = '/usr/bin/xcrun'
    try:
        gui = {}
        for item, expected in (('managername', 'Aqua'), ('manageruid', str(account.pw_uid))):
            raw, _ = run.command(item, ['/bin/launchctl', item], timeout=10)
            gui[item] = raw.decode().strip()
            need(gui[item] == expected, 'nonadministrator-aqua-context-required')
        console = Path('/dev/console').stat()
        need(console.st_uid == account.pw_uid, 'runner-must-own-console')
        result['execution_identity'] = {'uid': os.getuid(), 'euid': os.geteuid(), 'gid': os.getgid(),
            'egid': os.getegid(), 'posix_groups': posix_groups(), 'directory_groups': sorted(groups),
            'console_uid': console.st_uid, 'console_gid': console.st_gid, 'aqua': gui,
            'nonadministrator': True, 'home': account.pw_dir}
        write(run.evidence / 'execution-identity.json', result['execution_identity'])
        for name, command in [('flutter', [args.flutter, '--version', '--machine']),
                              ('xcode', [args.developer_dir / 'usr/bin/xcodebuild', '-version']),
                              ('maestro', [args.maestro, '--version'])]:
            raw, _ = run.command(name + '-version', command, timeout=90)
            if not raw:
                raw = (run.commands / (name + '-version.stderr.log')).read_bytes()
            result.setdefault('versions', {})[name] = raw.decode('utf-8', 'replace').strip()
        project = args.workdir / 'runner_hello_world'
        run.command('flutter-create', [args.flutter, 'create', '--empty', '--platforms=ios', '--org',
            'tech.uxmal', '--project-name', 'runner_hello_world', '--no-pub', str(project)], timeout=180)
        for name in FIXTURE:
            destination = project / name
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(args.fixture_root / name, destination)
            need(sha(destination) == FIXTURE[name], 'fixture-overlay-mismatch')
            evidence_copy = run.evidence / 'fixture' / name
            evidence_copy.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(destination, evidence_copy)
        write(run.evidence / 'fixture-overlay.json', {name: reference(project / name) for name in FIXTURE})
        run.command('flutter-pub-get', [args.flutter, 'pub', 'get'], cwd=project, timeout=300)
        need((project / 'pubspec.lock').is_file(), 'resolved-pub-lock-required')
        shutil.copyfile(project / 'pubspec.lock', run.evidence / 'pubspec.lock')
        run.command('flutter-build', [args.flutter, 'build', 'ios', '--simulator', '--debug',
                                      '--target', 'lib/main.dart'], cwd=project, timeout=1200)
        app = project / 'build/ios/iphonesimulator/Runner.app'
        need(app.is_dir(), 'built-simulator-app-missing')
        info = plistlib.loads((app / 'Info.plist').read_bytes())
        flow = (project / '.maestro/flows/hello-world.yaml').read_text()
        declared = re.match(r'appId:\s*([^\s]+)\s*\n', flow)
        need(declared and declared[1] == info.get('CFBundleIdentifier') == APP_ID,
             'built-bundle-id-must-match-executed-flow')
        need('iPhoneSimulator' in info.get('CFBundleSupportedPlatforms', []), 'simulator-platform-required')
        result['app'] = {'path': str(app), 'bundle_id': info['CFBundleIdentifier'],
            'platforms': info['CFBundleSupportedPlatforms'], 'info_plist': reference(app / 'Info.plist'),
            'executable': reference(app / info['CFBundleExecutable'])}
        for relative in ('Frameworks/App.framework/App', 'Frameworks/App.framework/flutter_assets/kernel_blob.bin'):
            if (app / relative).is_file():
                result['app'].setdefault('compiled_flutter_files', {})[relative] = reference(app / relative)
        source_records = {}
        excluded = {'build', '.dart_tool', 'Pods', '.symlinks', '.git'}
        for directory, directories, filenames in os.walk(project, followlinks=False):
            directories[:] = sorted(name for name in directories if name not in excluded
                                    and not (Path(directory) / name).is_symlink())
            for name in sorted(filenames):
                path = Path(directory) / name
                if path.is_file() and not path.is_symlink() and path.suffix in (
                        '.dart', '.yaml', '.lock', '.pbxproj', '.plist', '.xcconfig'):
                    source_records[str(path.relative_to(project))] = reference(path)
        write(run.evidence / 'generated-source-files.json', source_records)
        raw, _ = run.command('simulator-inventory', [xcrun, 'simctl', 'list', '--json'], timeout=30)
        inventory = json.loads(raw)
        runtime, phone = select_simulator(inventory)
        result['simulator_selection'] = {'runtime': runtime, 'device_type': phone}
        if runtime['identifier'] != 'com.apple.CoreSimulator.SimRuntime.iOS-26-5':
            result['warnings'].append('iOS26.5 unavailable; selected actual available runtime ' + runtime['identifier'])
        label = 'runner-image-qualification-' + uuid.uuid4().hex
        result['simulator_name'] = label
        previous_devices = device_inventory(raw)
        need(all(row.get('name') != label for row in previous_devices.values()), 'simulator-name-not-fresh')
        result['preexisting_simulator_udids'] = sorted(previous_devices)
        create_attempted = True
        raw, row = run.command('simulator-create', [xcrun, 'simctl', 'create', label,
             phone['identifier'], runtime['identifier']], timeout=60, check=False)
        candidate = raw.decode().strip()
        if UUID.fullmatch(candidate):
            simulator = candidate.upper()
            result['simulator_udid'] = simulator
            write(run.evidence / 'owned-simulator.json', {'udid': simulator, 'name': label,
                                                        'runtime': runtime['identifier']})
        need(row['exit_code'] == 0 and simulator is not None, 'owned-simulator-create-unconfirmed')
        run.command('simulator-boot', [xcrun, 'simctl', 'boot', simulator], timeout=30)
        run.command('simulator-bootstatus', [xcrun, 'simctl', 'bootstatus', simulator, '-b'], timeout=240)
        run.command('simulator-install', [xcrun, 'simctl', 'install', simulator, app], timeout=120)
        run.command('simulator-launch', [xcrun, 'simctl', 'launch', simulator, APP_ID], timeout=60)
        maestro = run.evidence / 'maestro'
        maestro.mkdir(mode=0o700)
        junit = maestro / 'junit.xml'
        _, row = run.command('maestro-test', [args.maestro, '--device', simulator, 'test',
            '--format', 'JUNIT', '--output', junit, '--test-output-dir', maestro,
            '--debug-output', maestro / 'debug', project / '.maestro/flows/hello-world.yaml'],
            cwd=project, timeout=360, check=False)
        screenshot_attempted = True
        run.command('simulator-screenshot', [xcrun, 'simctl', 'io', simulator, 'screenshot',
             run.evidence / 'hello-world-final.png'], timeout=30)
        need(row['exit_code'] == 0 and junit.is_file(), 'maestro-test-or-junit-failed')
        report = ET.parse(junit).getroot()
        cases = list(report.iter('testcase'))
        need(cases and not list(report.iter('failure')) and not list(report.iter('error'))
             and not list(report.iter('skipped')), 'maestro-junit-not-passed')
        result['maestro'] = {'exit_code': row['exit_code'], 'junit': reference(junit),
            'test_cases': len(cases), 'flow_sha256': sha(project / '.maestro/flows/hello-world.yaml'),
            'assertions': ['Hello World visible', 'Count: 0 visible', 'Increment tapped', 'Count: 1 visible']}
        result['status'] = 'passed'
    except BaseException as error:
        result.update(status='cancelled' if run.cancelled else 'failed', error_type=type(error).__name__,
                      reason=str(error) if isinstance(error, RuntimeError) else 'qualification-step-error')
    finally:
        cleanup = result['cleanup']
        if create_attempted and simulator is None:
            # A create response may be lost after CoreSimulator committed it.
            # Reconcile only the exact unique name and pre-creation inventory.
            try:
                raw, _ = run.command('cleanup-reconcile-create',
                    [xcrun, 'simctl', 'list', 'devices', '--json'], timeout=30, cleanup=True)
                candidates = [(udid, row) for udid, row in device_inventory(raw).items()
                    if row.get('name') == result['simulator_name']
                    and udid not in result['preexisting_simulator_udids']]
                if len(candidates) == 1:
                    simulator = candidates[0][0]
                    result['simulator_udid'] = simulator
                    cleanup['create_reconciled_by_exact_new_name'] = True
                    write(run.evidence / 'owned-simulator-reconciled.json',
                          {'udid': simulator, 'name': result['simulator_name']})
                elif not candidates:
                    cleanup['create_reconciled_absent'] = True
            except BaseException as error:
                cleanup['create_reconciliation_error_type'] = type(error).__name__
        if simulator is not None:
            if not screenshot_attempted:
                try:
                    run.command('failure-screenshot', [xcrun, 'simctl', 'io', simulator, 'screenshot',
                         run.evidence / 'failure-state.png'], timeout=20, check=False, cleanup=True)
                except BaseException:
                    cleanup['failure_screenshot_unavailable'] = True
            for operation in ('shutdown', 'delete'):
                try:
                    _, row = run.command('cleanup-' + operation, [xcrun, 'simctl', operation, simulator],
                                         timeout=60, check=False, cleanup=True)
                    cleanup[operation + '_exit_code'] = row['exit_code']
                except BaseException as error:
                    cleanup[operation + '_error_type'] = type(error).__name__
            try:
                raw, _ = run.command('cleanup-verify-absence', [xcrun, 'simctl', 'list', 'devices', '--json'],
                                     timeout=30, cleanup=True)
                cleanup['owned_simulator_absent'] = simulator not in device_inventory(raw)
            except BaseException:
                cleanup['owned_simulator_absent'] = False
        else:
            cleanup['owned_simulator_absent'] = not create_attempted or cleanup.get('create_reconciled_absent', False)
            if create_attempted and not cleanup['owned_simulator_absent']:
                cleanup['uncertainty'] = 'Simulator creation was attempted but its UDID was not confirmed.'
        cleanup['command_groups_confirmed'] = all(row.get('spawn_absent') or
            row['process_reaped'] and row['process_group_absent'] for row in run.rows)
        cleanup['confirmed'] = cleanup['owned_simulator_absent'] and cleanup['command_groups_confirmed']
        if result['status'] == 'passed' and not cleanup['confirmed']:
            result.update(status='failed', reason='qualification-cleanup-unconfirmed')
        result['finished_at_utc'] = now()
        result['commands'] = run.rows
        write(run.evidence / 'result.json', result)
        manifest = {str(path.relative_to(run.evidence)): reference(path)
            for path in sorted(run.evidence.rglob('*')) if path.is_file() and not path.is_symlink()}
        write(run.evidence / 'manifest.json', {'schema_version': 1, 'status': result['status'],
              'created_at_utc': now(), 'files': manifest})
        print(json.dumps({'status': result['status'], 'evidence': str(run.evidence),
                          'result_sha256': sha(run.evidence / 'result.json'),
                          'manifest_sha256': sha(run.evidence / 'manifest.json')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
