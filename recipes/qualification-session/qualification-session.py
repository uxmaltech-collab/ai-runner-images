#!/opt/macos-tart-bootstrap/python/bin/python3.12 -I
"""Qualification-only adapter around the unchanged canonical Session owner.

Install only in a disposable acceptance clone. This is not a runner, GitHub
registration, production guest adapter, or exportable-image preparation step.
"""
import copy
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import resource
import secrets
import signal
import stat
import subprocess
import sys
import time

ROOT = Path('/opt/ai-runner-qualification')
CONFIG = ROOT / 'qualification.json'
STATE = Path('/private/var/lib/ai-runner-qualification')
HELPER = ROOT / 'qualification-session.py'
SYSTEM = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8'}
SOURCE = '3a3e163793d85a2110a7de5098ffe2a2f90b2f3b'


def need(value, code):
    if not value:
        raise RuntimeError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def protected(path):
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
             'qualification-unprotected-directory')


def read(path, maximum=1024 * 1024):
    protected(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_nlink == 1
             and not before.st_mode & 0o022 and before.st_size <= maximum,
             'qualification-unprotected-file')
        raw = os.read(fd, maximum + 1)
        after = os.fstat(fd)
        need(len(raw) == before.st_size and (before.st_ino, before.st_size, before.st_mtime_ns)
             == (after.st_ino, after.st_size, after.st_mtime_ns), 'qualification-file-raced')
        return raw
    finally:
        os.close(fd)


def save(name, value):
    protected(STATE)
    path = STATE / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        raw = encoded(value)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)


def load():
    need(sys.platform == 'darwin' and os.getuid() == os.geteuid() == 0,
         'qualification-root-darwin-required')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.umask(0o077)
    config = json.loads(read(CONFIG))
    need(config['schema_version'] == 1 and config['qualification_only'] is True
         and config['image_export_permitted'] is False
         and config['repository'] == 'uxmaltech-collab/ai-runner-images'
         and config['session_source_commit'] == SOURCE, 'qualification-config-binding')
    need(re.fullmatch(r'[0-9a-f]{40}', config['recipe_commit']) is not None,
         'qualification-recipe-commit')
    manifest = json.loads(read(ROOT / 'MODULES.json'))
    need(manifest['source_commit'] == SOURCE, 'qualification-module-source')
    expected = {'__init__.py', 'tart_contract.py', 'tart_execution.py', 'tart_observation.py',
                'tart_session.py', 'tart_session_contract.py', 'tart_session_native.py'}
    need(set(manifest['modules']) == expected, 'qualification-module-closure')
    for name, record in manifest['modules'].items():
        raw = read(ROOT / 'lib' / 'runner_control_plane' / name)
        need(len(raw) == record['bytes'] and digest(raw) == record['sha256'],
             'qualification-module-digest')
    sys.path.insert(0, str(ROOT / 'lib'))
    from runner_control_plane import tart_session as owner
    from runner_control_plane import tart_session_contract as contract
    from runner_control_plane.tart_contract import JobRequest, Resources
    contract.validate_session_policy(config['session_policy'])
    need(config['session_policy']['runner']['name'] == config['guest_user']
         and config['session_policy']['runner']['home'] == config['guest_home'],
         'qualification-runner-policy')
    config['state_root'] = str(STATE)
    config['native_tool_probes_required'] = True
    config['guest_agent_sha256'] = digest(read(HELPER))
    # The existing owner has no SessionRequest type. Its JobRequest is a local
    # identity envelope here; these IDs are never registered or sent to GitHub.
    if (STATE / 'LOCAL-IDENTITY.json').exists():
        identity = json.loads(read(STATE / 'LOCAL-IDENTITY.json'))
        need(identity['github_job_created'] is False and identity['request']['repository'] == config['repository']
             and identity['configuration_sha256'] == digest(read(CONFIG)), 'qualification-identity-binding')
        request = JobRequest.from_dict(identity['request'])
    else:
        request = None
    return config, request, owner, contract, JobRequest, Resources


def resolve(config):
    account = pwd.getpwnam(config['guest_user'])
    policy = config['session_policy']['runner']
    groups = set(os.getgrouplist(account.pw_name, account.pw_gid))
    prohibited = {0}
    for name in ('admin', 'wheel', 'sudo'):
        try:
            prohibited.add(grp.getgrnam(name).gr_gid)
        except KeyError:
            pass
    need((account.pw_uid, account.pw_gid, account.pw_dir) ==
         (policy['uid'], policy['gid'], policy['home']) and not groups.intersection(prohibited),
         'qualification-runner-not-nonadmin')
    config.update(uid=account.pw_uid, gid=account.pw_gid, allowed_gids=sorted(groups))
    return config


def gui_prefix(config, operation):
    return ['/bin/launchctl', 'asuser', str(config['uid']), str(HELPER), operation]


def require_gui(config, run=subprocess.run):
    result = run(gui_prefix(config, 'gui-probe'), stdin=subprocess.DEVNULL,
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12, check=False, env=SYSTEM)
    need(result.returncode == 0 and result.stdout == b'{"status":"gui-ready"}\n',
         'qualification-gui-unavailable')


def tool_bytes(config, name):
    tool = config['tools'][name]
    path = Path(tool['path'])
    need(path.is_absolute(), 'qualification-tool-path')
    # Executables may be regular launchers or links within a protected tree.
    target = path.resolve(strict=True)
    protected(path.parent.resolve(strict=True))
    actual = digest(read(target, 512 * 1024 * 1024))
    need(actual == tool['sha256'], 'qualification-tool-digest')
    return actual


def provenance(config, run=subprocess.run):
    hashes = {name: tool_bytes(config, name) for name in config['tools']}
    result = {'qualification_only': True, 'source_commit': SOURCE,
              'guest_agent_sha256': config['guest_agent_sha256'], 'tool_sha256': hashes,
              'tool_probe_warnings': [], 'tools': {}}
    need(run is not None, 'qualification-interrupted-tool-probe-not-accepted')
    for name, tool in config['tools'].items():
        answer = run(gui_prefix(config, 'gui-version') + [name], stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False, env=SYSTEM)
        output = (answer.stdout + answer.stderr).decode('utf-8', 'replace').strip()
        need(answer.returncode == 0 and len(output) <= 16384 and tool['version_contains'] in output,
             'qualification-tool-version-failed')
        result['tools'][name] = {'output': output, 'sha256': hashes[name]}
    return result


def environment(config):
    value = dict(config['environment'])
    need(not any(re.search(r'TOKEN|SECRET|PASSWORD|API_KEY|AUTH', key) for key in value),
         'qualification-secret-environment-forbidden')
    value.update(HOME=config['guest_home'], USER=config['guest_user'], LOGNAME=config['guest_user'],
                 LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8', CI='true',
                 MAESTRO_CLI_NO_ANALYTICS='1', MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED='true')
    need(all(isinstance(k, str) and isinstance(v, str) and '\x00' not in k + v
             for k, v in value.items()), 'qualification-environment-shape')
    return value


def gui_worker(config, operation, argument):
    config = resolve(config)
    for name, expected in (('managername', b'Aqua'), ('manageruid', str(config['uid']).encode())):
        value = subprocess.run(['/bin/launchctl', name], stdin=subprocess.DEVNULL, capture_output=True,
                               timeout=5, env=SYSTEM, check=False)
        need(value.returncode == 0 and value.stdout.strip() == expected, 'qualification-aqua-context')
    if operation == 'gui-probe':
        print('{"status":"gui-ready"}')
        return
    if operation == 'gui-version':
        tool = config['tools'][argument]
        tool_bytes(config, argument)
        argv, cwd = [tool['path'], *tool['version_args']], config['guest_home']
    else:
        path = Path(argument)
        need(path.parent == ROOT / 'commands' and re.fullmatch(r'[a-z0-9-]+\.json', path.name),
             'qualification-command-path')
        command = json.loads(read(path, 65536))
        need(set(command) == {'tool', 'args', 'cwd'} and command['tool'] in config['tools']
             and isinstance(command['args'], list) and all(isinstance(v, str) and '\x00' not in v
             for v in command['args']), 'qualification-command-shape')
        tool = config['tools'][command['tool']]
        tool_bytes(config, command['tool'])
        argv, cwd = [tool['path'], *command['args']], command['cwd']
        need(Path(cwd).is_relative_to(Path(config['guest_home'])) and Path(cwd).resolve() == Path(cwd),
             'qualification-working-directory')
    env = environment(config)
    # Match the production guest owner's narrow POSIX group drop; never retain
    # ambient root groups or expand supplementary Directory Services groups.
    os.setgroups([])
    os.setgid(config['gid'])
    os.setuid(config['uid'])
    from runner_control_plane.tart_session_native import native_posix_groups
    need(os.getuid() == os.geteuid() == config['uid'] and os.getgid() == os.getegid() == config['gid']
         and native_posix_groups() == [config['gid']], 'qualification-credential-drop')
    os.chdir(cwd)
    os.execve(argv[0], argv, env)


def main():
    operation = sys.argv[1]
    config, request, owner, contract, JobRequest, Resources = load()
    if operation == 'session-native':
        frame = owner.read_private_frame(sys.stdin.buffer, 15, 8192, lambda: None)
        try:
            print(encoded(owner.native_worker(config, frame)).decode(), end='')
        finally:
            contract.wipe_credentials({'frame': frame})
        return
    if operation.startswith('gui-'):
        need(operation in ('gui-probe', 'gui-version', 'gui-exec'), 'qualification-gui-operation')
        gui_worker(config, operation, None if len(sys.argv) == 2 else sys.argv[2])
        return
    need(operation in ('prepare', 'shutdown', 'status'), 'qualification-operation')
    if operation == 'prepare':
        need(request is None and not (STATE / 'session-v2').exists(), 'qualification-prepare-already-consumed')
        need(STATE.exists(), 'qualification-state-root-not-installed')
        nonce = secrets.token_hex(16)
        local_id = str(time.time_ns())
        request = JobRequest(operation='status', job_id=local_id, run_id=local_id, run_attempt=1,
            lease_id=nonce, generation=1, repository=config['repository'], profile='image-qualification',
            source_repository=config['repository'], source_commit=config['recipe_commit'],
            app_commit=config['recipe_commit'], workflow_commit=config['recipe_commit'],
            image=config['image'], resources=Resources.from_dict(config['resources']),
            deadline_unix=config['deadline_unix'], runner_name='qualification-' + nonce,
            job_label='tart-job-' + nonce)
        save('LOCAL-IDENTITY.json', {'schema_version': 1, 'qualification_only': True,
             'github_job_created': False, 'jit_created': False, 'image_export_permitted': False,
             'configuration_sha256': digest(read(CONFIG)), 'request': request.as_dict()})
    need(request is not None, 'qualification-prepare-required')
    operations = owner.DarwinOperations(config, request, helper_path=str(HELPER),
        resolve_account=resolve, require_gui=require_gui, check_provenance=provenance)
    session = owner.Session(config, request, operations)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, operations.commands.interrupt)
    if operation == 'prepare':
        credentials = {role: bytearray(secrets.token_urlsafe(48), 'ascii')
                       for role in ('provisioner', 'runner')}
        try:
            response = session.prepare(credentials)
        finally:
            contract.wipe_credentials(credentials)
    elif operation == 'shutdown':
        response = session.shutdown()
    else:
        response = session.status()
    save(operation + '-' + str(time.time_ns()) + '.json', {'qualification_only': True,
         'github_job_created': False, 'image_export_permitted': False, 'response': response})
    print(encoded(response).decode(), end='')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Owner exceptions already use public reason codes. Never emit native
        # error text, credential frames, account hashes or arbitrary argv.
        text = str(error)
        code = text if re.fullmatch(r'[a-z][a-z0-9-]{0,100}', text) else 'qualification-operation-failed'
        print(json.dumps({'passed': False, 'reason_code': code, 'error_type': type(error).__name__}))
        raise SystemExit(2)
