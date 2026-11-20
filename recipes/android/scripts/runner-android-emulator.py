#!/usr/bin/env python3
"""Own one temporary Android emulator for a command inside an ephemeral runner."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time

SERIAL = 'emulator-5554'
SYSTEM_IMAGE = 'system-images;android-36;google_apis;x86_64'
MARKER = 'RUNNER_ANDROID_EMULATOR_OWNED'
MARKER_ALIASES = 'RUNNER_ANDROID_EMULATOR_OWNED_ALIASES'
# The image-owned list written at build time from the planner's input. A journey launcher
# starts this helper with a fixed list of environment variables, so the list cannot rely
# on the environment alone.
MARKER_ALIASES_FILE = Path('/etc/runner-android-emulator/marker-aliases')


def listed_aliases(environment):
    """Names from the environment (explicit input) and from the image-owned file, in that order."""
    names = environment.get(MARKER_ALIASES, '').split()
    try:
        names += MARKER_ALIASES_FILE.read_text(encoding='utf-8').split()
    except FileNotFoundError:
        pass
    except (OSError, UnicodeError) as error:
        print(f'WARNING: the ownership marker alias list {MARKER_ALIASES_FILE} cannot be read '
              f'({type(error).__name__}); only the neutral marker is exported for it', file=sys.stderr)
    return names


def marker_aliases(environment, taken):
    """The former ownership-marker names a consumer's validator still reads.

    They are organization data, listed by the planner (names separated by spaces) in the
    image-owned file written at build time, or in MARKER_ALIASES when the caller passes
    it, and exported with the same value as MARKER. A name that is not an environment
    variable name, or that would replace a variable already set, warns and is skipped;
    the marker itself is always exported.
    """
    names = {}
    for name in listed_aliases(environment):
        if name in names:
            continue
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', name):
            print(f'WARNING: ignored the ownership marker alias {name!r}: not an environment variable name', file=sys.stderr)
        elif name in taken:
            print(f'WARNING: ignored the ownership marker alias {name}: it would replace a variable already set', file=sys.stderr)
        else:
            names[name] = '1'
    return names


def kvm_access():
    """Require the group supplied by the leaf's unprivileged JIT bootstrap."""
    try:
        device = Path('/dev/kvm').stat()
    except FileNotFoundError as exc:
        raise RuntimeError('Journey requires the declared /dev/kvm device mapping') from exc
    if not stat.S_ISCHR(device.st_mode):
        raise RuntimeError('/dev/kvm is not a character device')
    if os.geteuid() == 0:
        raise RuntimeError('Run the journey as the unprivileged runner user')
    if os.access('/dev/kvm', os.R_OK | os.W_OK):
        return
    raise RuntimeError('Mapped /dev/kvm is inaccessible; use the Android image entrypoint')


def adb(arguments, environment, timeout=10):
    return subprocess.run(['adb', '-s', SERIAL, *arguments], env=environment,
                          capture_output=True, text=True, timeout=timeout, check=False)


def stop_owned(process, timeout):
    """Terminate only a process group created by this wrapper and reap it."""
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def execute(command, log_dir, boot_timeout=600, shutdown_timeout=20):
    log_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = log_dir / 'emulator-result.json'
    if receipt_path.exists():
        raise RuntimeError('Use a new log directory; an emulator receipt already exists')
    receipt = {'schema_version': 1, 'serial': SERIAL, 'booted': False,
               'command_exit_code': None, 'cleanup_confirmed': False}
    emulator = child = None
    previous = {}
    temporary_state = tempfile.TemporaryDirectory(prefix='android-journey-')
    exit_code = 1

    def interrupted(signum, frame):
        raise InterruptedError(signum)

    for signum in (signal.SIGTERM, signal.SIGINT):
        previous[signum] = signal.signal(signum, interrupted)
    try:
        state = Path(temporary_state.name)
        environment = dict(os.environ, ANDROID_SERIAL=SERIAL,
                           ANDROID_AVD_HOME=str(state / 'avd'),
                           ANDROID_USER_HOME=str(state / 'android'),
                           ANDROID_EMULATOR_HOME=str(state / 'android'),
                           **{MARKER: '1'})
        environment.update(marker_aliases(os.environ, environment))
        for directory in ('avd', 'android'):
            (state / directory).mkdir(mode=0o700)
        # Containers have separate network namespaces. Still refuse a
        # pre-existing device rather than adopting or stopping it.
        if adb(['get-state'], environment).returncode == 0:
            raise RuntimeError(f'{SERIAL} already exists; refusing to adopt it')
        with (log_dir / 'avd-create.log').open('xb') as avd_log:
            subprocess.run(['avdmanager', 'create', 'avd', '--name', 'journey',
                            '--package', SYSTEM_IMAGE, '--device', 'pixel_7'],
                           input=b'no\n', env=environment, stdout=avd_log,
                           stderr=subprocess.STDOUT, timeout=90, check=True)
        with (log_dir / 'emulator.log').open('xb') as emulator_log:
            emulator = subprocess.Popen(
                ['emulator', '-avd', 'journey', '-port', '5554', '-no-window',
                 '-no-audio', '-no-boot-anim', '-no-snapshot', '-wipe-data',
                 '-gpu', 'swiftshader', '-accel', 'on', '-cores', '4',
                 '-memory', '3072', '-camera-back', 'none', '-camera-front', 'none'],
                env=environment, stdout=emulator_log, stderr=subprocess.STDOUT,
                start_new_session=True)
            deadline = time.monotonic() + boot_timeout
            while time.monotonic() < deadline:
                if emulator.poll() is not None:
                    raise RuntimeError(f'Emulator exited before boot ({emulator.returncode})')
                try:
                    result = adb(['shell', 'getprop', 'sys.boot_completed'], environment)
                    if result.returncode == 0 and result.stdout.strip() == '1':
                        receipt['booted'] = True
                        break
                except subprocess.TimeoutExpired:
                    pass
                time.sleep(2)
            if not receipt['booted']:
                raise RuntimeError(f'Emulator boot exceeded {boot_timeout} seconds')
            # Animation settings improve deterministic interaction. Failure
            # is a warning; the real app tests retain their own outcome.
            for name in ('window_animation_scale', 'transition_animation_scale', 'animator_duration_scale'):
                try:
                    result = adb(['shell', 'settings', 'put', 'global', name, '0'], environment)
                    if result.returncode:
                        print(f'WARNING: could not set {name}', file=sys.stderr)
                except subprocess.TimeoutExpired:
                    print(f'WARNING: timed out setting {name}', file=sys.stderr)
            child = subprocess.Popen(command, env=environment, start_new_session=True)
            receipt['command_exit_code'] = child.wait()
            exit_code = receipt['command_exit_code'] if receipt['command_exit_code'] >= 0 else 128 - receipt['command_exit_code']
    except InterruptedError as exc:
        receipt['error'] = 'interrupted'
        exit_code = 128 + int(exc.args[0])
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        receipt['error'] = str(exc)
        print(f'ERROR: {exc}', file=sys.stderr)
        exit_code = 1
    finally:
        # Cleanup also runs after boot failure, cancellation and command failure.
        # Defer further interruption until the owned processes have been reaped.
        for signum in previous:
            signal.signal(signum, signal.SIG_IGN)
        try:
            cleanup_errors = []
            for owned in (child, emulator):
                try:
                    stop_owned(owned, shutdown_timeout)
                except (OSError, subprocess.SubprocessError) as exc:
                    cleanup_errors.append(str(exc))
            if not cleanup_errors:
                temporary_state.cleanup()
                receipt['cleanup_confirmed'] = True
            else:
                receipt['cleanup_errors'] = cleanup_errors
                exit_code = exit_code or 1
                print('ERROR: emulator cleanup is incomplete', file=sys.stderr)
        finally:
            with receipt_path.open('x') as output:
                json.dump(receipt, output, indent=2)
                output.write('\n')
            for signum, handler in previous.items():
                signal.signal(signum, handler)
    return exit_code


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-dir', type=Path, required=True)
    parser.add_argument('--boot-timeout', type=int, default=600)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    command = arguments.command[1:] if arguments.command[:1] == ['--'] else arguments.command
    if not command:
        parser.error('a command after -- is required')
    if not 1 <= arguments.boot_timeout <= 1200:
        parser.error('--boot-timeout must be between 1 and 1200 seconds')
    kvm_access()
    return execute(command, arguments.log_dir.resolve(), arguments.boot_timeout)


if __name__ == '__main__':
    raise SystemExit(main())
