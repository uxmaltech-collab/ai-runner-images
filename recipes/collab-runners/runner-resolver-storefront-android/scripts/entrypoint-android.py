#!/usr/bin/python3 -I
"""Set the mapped KVM group once, then enter the inherited JIT runner as 1001."""
import os
from pathlib import Path
import pwd
import stat
import sys


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


def main():
    command = entrypoint_argv(sys.argv[1:])
    os.environ['HOME'] = '/home/runner'
    os.environ['USER'] = os.environ['LOGNAME'] = 'runner'
    os.execv(command[0], command)


if __name__ == '__main__':
    main()
