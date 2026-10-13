#!/usr/bin/python3 -I
"""Set the mapped KVM group once, then enter the inherited JIT runner as 1001."""
import json
import os
from pathlib import Path
import pwd
import stat
import sys

GRADLE_HOME = Path('/tmp/gradle-home')


def entrypoint_argv(arguments):
    if os.geteuid() != 0:
        raise RuntimeError('Android bootstrap must start as root and immediately drop to runner')
    account = pwd.getpwnam('runner')
    if account.pw_uid != 1001 or account.pw_gid != 1001:
        raise RuntimeError('Unexpected inherited runner identity')
    groups = set(os.getgrouplist('runner', account.pw_gid))
    try:
        device = Path('/dev/kvm').stat()
    except FileNotFoundError:
        device = None  # Resolve does not require a VM or a mapped KVM device.
    if device is not None:
        if not stat.S_ISCHR(device.st_mode):
            raise RuntimeError('Mapped /dev/kvm must be a character device')
        groups.add(device.st_gid)
    return ['/usr/bin/setpriv', '--reuid', '1001', '--regid', '1001',
            '--groups', ','.join(map(str, sorted(groups))), '--no-new-privs',
            '--', '/entrypoint.sh', *arguments]


def gradle_seed_environment(seed, home=GRADLE_HOME, owner=(1001, 1001)):
    """Let a job run the repository's Gradle wrapper without the network.

    The controller mounts a tool seed read-only: the Gradle distribution and
    the dependencies a rollout fetched on the host. The wrapper locks the
    directory of its distribution and Gradle writes its own caches, so the
    Gradle home is a new directory under /tmp, which a sandboxed command may
    write. It holds only the wrapper's marker and a link to the distribution.
    A seed this image cannot use changes nothing: the job then needs the network.
    """
    try:
        gradle = json.loads((seed / 'manifest.json').read_text())['gradle']
        distribution = seed / gradle['distribution']
        cache = seed / gradle['ro_dep_cache']
        kept = home / 'wrapper' / 'dists' / gradle['wrapper_directory']
        archive = gradle['archive_name']
        if not (distribution / 'bin' / 'gradle').is_file() or not (cache / 'modules-2').is_dir():
            raise ValueError('the seed carries no distribution or no dependency cache')
        if '..' in Path(gradle['wrapper_directory']).parts or '/' in archive:
            raise ValueError('the seed names a path outside the Gradle home')
        kept.mkdir(parents=True)
        (kept / distribution.name).symlink_to(distribution)
        (kept / (archive + '.ok')).touch()
        for path in (home, *home.rglob('*')):
            os.chown(path, *owner, follow_symlinks=False)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'tool seed not used: {type(error).__name__}: {error}', file=sys.stderr)
        return {}
    return {'GRADLE_USER_HOME': str(home), 'GRADLE_RO_DEP_CACHE': str(cache)}


def main():
    command = entrypoint_argv(sys.argv[1:])
    seed = os.environ.get('COLLAB_TOOL_SEED')
    if seed:
        os.environ.update(gradle_seed_environment(Path(seed)))
    os.environ['HOME'] = '/home/runner'
    os.environ['USER'] = os.environ['LOGNAME'] = 'runner'
    os.execv(command[0], command)


if __name__ == '__main__':
    main()
