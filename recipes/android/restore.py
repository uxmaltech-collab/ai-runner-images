#!/usr/bin/env python3
"""Restore a local Android image archive in new stores and a private network namespace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def restore(build_path, evidence):
    build = json.loads(build_path.read_text())
    archive = build_path.parent / build['archive']['file']
    if archive.stat().st_size != build['archive']['bytes'] or sha(archive) != build['archive']['sha256']:
        raise ValueError('Local archive integrity mismatch')
    evidence.mkdir(mode=0o700, parents=False, exist_ok=False)
    runtime = Path(tempfile.mkdtemp(prefix='android-restore-'))
    env = {'PATH': os.environ['PATH'], 'HOME': str(runtime), 'DOCKER_CONFIG': str(runtime / 'client')}
    client = ['docker', '--host', 'unix://' + str(runtime / 'docker.sock')]
    result = {'schema_version': 1, 'status': 'failed', 'initial_store': 'empty',
              'archive_sha256': sha(archive), 'build_receipt_sha256': sha(build_path),
              'credentials': 'none', 'github_e2e': 'not-run', 'distribution': 'local-only'}
    processes = []; logs = []
    def host_bridge():
        links = json.loads(subprocess.check_output(['ip', '-j', 'link', 'show']))
        return [link for link in links if link['ifname'] == 'docker0']

    bridge_before = host_bridge()

    def command(argv, name, timeout=60):
        (evidence / (name + '.command.json')).write_text(json.dumps(argv, indent=2) + '\n')
        with (evidence / (name + '.log')).open('xb') as output:
            completed = subprocess.run(argv, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        if completed.returncode:
            raise ValueError(f'{name} failed: {completed.returncode}; see preserved log')
        return (evidence / (name + '.log')).read_bytes()

    def docker(args, name, timeout=60):
        return command(client + args, name, timeout)

    def start(argv, name):
        log = (evidence / (name + '.log')).open('xb'); logs.append(log)
        (evidence / (name + '.command.json')).write_text(json.dumps(argv, indent=2) + '\n')
        process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
        processes.append((name, process)); return process

    try:
        namespace = start(['unshare', '--net', '--', 'sleep', 'infinity'], 'namespace')
        for _ in range(40):
            if namespace.poll() is not None:
                raise ValueError('Private network namespace owner exited')
            own = os.readlink(f'/proc/{namespace.pid}/ns/net')
            if own != os.readlink('/proc/self/ns/net'):
                break
            time.sleep(0.05)
        else:
            raise ValueError('Refusing to launch Docker in the host network namespace')
        result['network_namespace'] = own
        isolated = ['nsenter', '--target', str(namespace.pid), '--net', '--']
        command(isolated + ['ip', 'link', 'set', 'lo', 'up'], 'loopback')
        start(isolated + ['containerd', '--config', '/dev/null', '--address', str(runtime / 'containerd.sock'),
                         '--root', str(evidence / 'containerd'), '--state', str(runtime / 'containerd-state')],
              'containerd')
        config = runtime / 'daemon.json'
        config.write_text(json.dumps({'features': {'containerd-snapshotter': True}}))
        daemon = start(isolated + ['dockerd', '--config-file', str(config),
            '--data-root', str(evidence / 'store'), '--exec-root', str(runtime / 'run'),
            '--pidfile', str(runtime / 'daemon.pid'), '--containerd', str(runtime / 'containerd.sock'),
            '--containerd-namespace', runtime.name, '--containerd-plugins-namespace', runtime.name + '-plugins',
            '--host', 'unix://' + str(runtime / 'docker.sock'), '--bridge', 'none',
            '--iptables=false', '--ip6tables=false', '--ip-forward=false', '--ip-masq=false'], 'dockerd')
        for _ in range(60):
            if daemon.poll() is not None:
                raise ValueError('Private Docker daemon exited')
            ready = subprocess.run(client + ['info'], env=env, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=3)
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise ValueError('Private Docker daemon not ready')
        if docker(['image', 'ls', '-q'], 'initial-images').strip():
            raise ValueError('Restore store must start empty')
        docker(['image', 'load', '-i', str(archive)], 'load', 900)
        expected = build['image']; ref = expected['reference']
        actual = json.loads(docker(['image', 'inspect', ref], 'image-inspect'))[0]
        if actual['Id'] != expected['id'] or actual['RootFS']['Layers'] != expected['layers']:
            raise ValueError('Restored image identity or layers differ')
        result['image_identity'] = 'matched'
        common = ['run', '--rm', '--pull', 'never', '--network', 'none', '--user', '1001:1001',
                  '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '6g', '--cpus', '4']
        uid = docker(common + ['--entrypoint', 'id', ref, '-u'], 'runner-uid').strip()
        if uid != b'1001':
            raise ValueError('Restored tools must run as UID1001')
        docker(common + ['--entrypoint', '/usr/local/bin/runner-android-stack-probe', ref], 'stack-probe', 120)
        for harness in ('claude', 'codex', 'grok'):
            docker(common + ['--entrypoint', harness, ref, '--version'], harness, 60)
        result.update(status='passed', runner_uid=1001, tool_launch='passed',
                      harness_versions='passed-offline', emulator_boot='not-run',
                      application_build='not-run', containers_remaining=[])
        result['containers_remaining'] = docker(['ps', '-aq'], 'containers-after').decode().splitlines()
        if result['containers_remaining']:
            raise ValueError('Owned fixture containers remain')
    except Exception as error:
        result.update(status='failed', error=str(error))
        raise
    finally:
        cleanup = {}
        for name, process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    result['status'] = 'cleanup-failed'
            cleanup[name] = {'pid': process.pid, 'stopped': process.poll() is not None}
        for log in logs:
            log.close()
        result['process_cleanup'] = cleanup
        # Compare persistent link identity; traffic counters are not in ip link's default output.
        result['host_bridge_preserved'] = bridge_before == host_bridge()
        if not result['host_bridge_preserved']:
            result['status'] = 'host-network-drift'
        (evidence / 'RESTORE.json').write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'passed':
        raise ValueError('Restoration or owned cleanup incomplete')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-receipt', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.build_receipt.resolve(), args.evidence.resolve()), indent=2))
