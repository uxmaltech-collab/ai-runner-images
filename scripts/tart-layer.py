#!/usr/bin/env python3
"""Small CLI composition wrapper; uses an installed Tart owner and explicit host binding.

This does not install accounts/services, change executor configuration, or admit
an image. VM copies and stopped artifact manifests remain separate from runtime
admission. Each invocation writes its own command/result receipt.
"""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import pwd
import re
from pathlib import Path
import subprocess
import sys
import time


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--vm', required=True)
    parser.add_argument('operation', choices=['clone', 'boot', 'exec', 'stop', 'seal', 'inspect'])
    parser.add_argument('--source', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--source-commit')
    parser.add_argument('--parent-digest')
    parser.add_argument('--parent-manifest', type=Path)
    argv = sys.argv[1:]
    separator = argv.index('--') if '--' in argv else len(argv)
    args = parser.parse_args(argv[:separator])
    args.command = argv[separator + 1:]
    assert not args.command or args.operation == 'exec'
    binding = json.loads(args.binding.read_text())
    account = pwd.getpwnam(binding['user'])
    assert (account.pw_uid, account.pw_gid) == (binding['uid'], binding['gid'])
    assert args.vm and all(c.isalnum() or c == '-' for c in args.vm)
    assert not args.receipt.exists(), 'Existing receipt must be reconciled, not overwritten'
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    root = Path(binding['tart_home']) / 'vms'
    target = root / args.vm
    assert root.is_dir() and not target.is_symlink()
    assert root.stat().st_uid == binding['uid'] and not root.stat().st_mode & 0o022
    env = {'HOME': binding['tart_child_home'], 'TART_HOME': binding['tart_home'],
           'TART_NO_AUTO_PRUNE': '1', 'LANG': 'en_US.UTF-8', 'PATH': binding['path']}
    prefix = ['/usr/bin/sudo', '-n', '-u', binding['user'], '/usr/bin/env', '-i',
              *[k + '=' + v for k, v in env.items()], binding['tart_binary']]
    result = {'schema_version': 1, 'operation': args.operation, 'vm': args.vm,
              'started_at': now(), 'status': 'started', 'commands': [],
              'binding_sha256': digest(args.binding), 'runtime_admission': False}

    def save():
        temporary = args.receipt.with_suffix('.writing')
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        temporary.replace(args.receipt)

    def run(argv, timeout=120, input_path=None):
        record = {'argv': argv, 'started_at': now()}
        result['commands'].append(record)
        save()
        timed_out = False
        try:
            with contextlib.ExitStack() as stack:
                source = stack.enter_context(input_path.open('rb')) if input_path else subprocess.DEVNULL
                p = subprocess.run(argv, stdin=source, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            timed_out = True
            p = subprocess.CompletedProcess(argv, 124, error.stdout or b'', error.stderr or b'')
            record['timeout_seconds'] = timeout
            record['remote_completion_uncertain'] = args.operation == 'exec'
        stem = args.receipt.with_suffix('')
        index = len(result['commands'])
        for suffix, raw in [('stdout', p.stdout), ('stderr', p.stderr)]:
            path = Path(str(stem) + f'.{index}.{suffix}')
            path.write_bytes(raw)
            record[suffix] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        record.update(exit_code=p.returncode, finished_at=now())
        save()
        if timed_out:
            raise TimeoutError('Command timed out; partial output retained; reconcile remote completion')
        if p.returncode:
            raise RuntimeError(f'Command exited {p.returncode}; inspect retained output')
        return p.stdout

    def stopped():
        row = json.loads(run(prefix + ['get', args.vm, '--format', 'json']))
        assert row['Running'] is False and row['State'] == 'stopped', row

    save()
    tuple_lock = None
    try:
        if args.operation == 'clone':
            assert args.source and args.source.is_dir() and not target.exists()
            assert args.source.stat().st_dev == root.stat().st_dev
            tuple_lock = os.open(args.source / 'config.json', os.O_RDWR | os.O_NOFOLLOW)
            fcntl.lockf(tuple_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            source = {n: (args.source / n).stat() for n in ['config.json', 'nvram.bin', 'disk.img']}
            holders = subprocess.run(['/usr/sbin/lsof', '-t', str(args.source / 'disk.img')], capture_output=True)
            assert holders.returncode == 1 and not holders.stdout and not holders.stderr, 'Source has active holders or lsof failed'
            target.mkdir(mode=0o700)
            os.chown(target, binding['uid'], binding['gid'])
            for name, before in source.items():
                dest = target / name
                run(['/bin/cp', '-c', str(args.source / name), str(dest)])
                os.chown(dest, binding['uid'], binding['gid'])
                os.chmod(dest, 0o600)
                assert dest.stat().st_ino != before.st_ino and dest.stat().st_size == before.st_size
                after = (args.source / name).stat()
                assert (after.st_ino, after.st_mtime_ns, after.st_size) == (before.st_ino, before.st_mtime_ns, before.st_size)
            os.close(tuple_lock); tuple_lock = None
            run(prefix + ['set', args.vm, '--cpu', str(binding['cpu']), '--memory', str(binding['memory_mib'])])
            stopped()
            result.update(source=str(args.source), destination=str(target), original_metadata_preserved=True, method='APFS-copy-on-write')
        elif args.operation == 'boot':
            stopped()
            stdout = args.receipt.with_suffix('.vm.stdout').open('xb')
            stderr = args.receipt.with_suffix('.vm.stderr').open('xb')
            argv = prefix + ['run', args.vm, '--no-graphics', '--no-audio', '--no-clipboard'] + binding['network_args']
            p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True, close_fds=True)
            stdout.close(); stderr.close()
            result.update(pid=p.pid, boot_argv=argv)
            save()
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                if p.poll() is not None:
                    raise RuntimeError('VM exited before RPC readiness')
                try:
                    probe = subprocess.run(prefix + ['exec', args.vm, '/usr/bin/id', '-u'], capture_output=True, timeout=8)
                except subprocess.TimeoutExpired:
                    time.sleep(2)
                    continue
                if probe.returncode == 0 and probe.stdout == b'0\n':
                    result['guest_boot_uuid'] = run(prefix + ['exec', args.vm, '/usr/sbin/sysctl', '-n', 'kern.bootsessionuuid']).decode().strip()
                    break
                time.sleep(2)
            else:
                raise RuntimeError('RPC readiness deadline exceeded; reconcile owned VM')
        elif args.operation == 'exec':
            assert args.command
            run(prefix + ['exec', '-i', args.vm] + args.command, timeout=args.timeout, input_path=args.input)
        elif args.operation == 'stop':
            run(prefix + ['stop', args.vm], timeout=args.timeout)
            stopped()
        elif args.operation == 'seal':
            stopped()
            assert args.source_commit and re.fullmatch('[0-9a-f]{40}', args.source_commit)
            assert args.parent_digest and re.fullmatch('[0-9a-f]{64}', args.parent_digest)
            assert args.parent_manifest and digest(args.parent_manifest) == args.parent_digest
            tuple_lock = os.open(target / 'config.json', os.O_RDWR | os.O_NOFOLLOW)
            fcntl.lockf(tuple_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            holders = subprocess.run(['/usr/sbin/lsof', '-t', str(target / 'disk.img')], capture_output=True)
            assert holders.returncode == 1 and not holders.stdout and not holders.stderr
            files = {}
            for name in ['config.json', 'nvram.bin', 'disk.img']:
                file = target / name
                before = file.stat()
                files[name] = {'bytes': before.st_size, 'sha256': digest(file)}
                after = file.stat()
                assert (before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns)
            os.close(tuple_lock); tuple_lock = None
            stopped()
            manifest = {'schema_version': 1, 'kind': 'tart-layer-artifact', 'files': files,
                        'source_repository': 'uxmaltech-collab/ai-runner-images',
                        'recipe_commit': args.source_commit, 'parent_manifest_sha256': args.parent_digest,
                        'runtime_admission': False}
            raw = (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode()
            path = args.receipt.with_suffix('.manifest.json')
            path.write_bytes(raw)
            result.update(manifest=manifest, manifest_path=str(path), manifest_sha256=hashlib.sha256(raw).hexdigest())
        else:
            result['inventory'] = json.loads(run(prefix + ['get', args.vm, '--format', 'json']))
        result['status'] = 'complete'
    except BaseException as error:
        result.update(status='failed', error_type=type(error).__name__, error=str(error))
        if args.operation == 'boot' and result.get('pid'):
            try:
                run(prefix + ['stop', args.vm], timeout=60)
                result['failed_boot_owned_vm_stopped'] = True
            except BaseException as cleanup_error:
                result['cleanup_uncertainty'] = str(cleanup_error)
        raise
    finally:
        if tuple_lock is not None:
            os.close(tuple_lock)
        result['finished_at'] = now()
        save()
    print(json.dumps({'receipt': str(args.receipt), 'sha256': digest(args.receipt), 'status': result['status']}))


if __name__ == '__main__':
    main()
