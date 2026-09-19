"""Exercise owned deletion without invoking Tart or altering host bindings."""
import importlib.util
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys

import pytest

SPEC = importlib.util.spec_from_file_location('tart_layer_test', Path(__file__).with_name('tart-layer.py'))
owner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(owner)


@pytest.mark.parametrize('condition', ['stopped', 'running', 'holder', 'delete-failed'])
def test_delete_uses_binding_and_only_stopped_unheld_target(tmp_path, monkeypatch, condition):
    root = tmp_path / 'vms'
    root.mkdir(mode=0o700)
    target = root / 'owned-child'
    target.mkdir()
    (target / 'config.json').write_bytes(b'fixture')
    (target / 'disk.img').write_bytes(b'fixture')
    sibling = root / 'original'
    sibling.mkdir()
    account = pwd.getpwuid(os.getuid())
    binding = tmp_path / 'binding.json'
    binding.write_text(json.dumps({'user': account.pw_name, 'uid': account.pw_uid, 'gid': account.pw_gid,
        'tart_home': str(tmp_path), 'tart_child_home': '/declared/home', 'path': '/declared/bin',
        'tart_binary': '/declared/tart'}))
    receipt = tmp_path / 'delete.json'
    monkeypatch.setattr(sys, 'argv', ['tart-layer.py', '--binding', str(binding), '--receipt', str(receipt),
                                    '--vm', 'owned-child', 'delete'])
    calls = []
    real_run = subprocess.run
    def run(argv, **kwargs):
        calls.append(argv)
        code, out = 0, b''
        if argv[0] == '/usr/sbin/lsof':
            code, out = (0, b'123\n') if condition == 'holder' else (1, b'')
        elif 'get' in argv:
            out = json.dumps({'Running': condition == 'running',
                              'State': 'running' if condition == 'running' else 'stopped'}).encode()
        elif 'delete' in argv:
            assert argv[-2:] == ['delete', 'owned-child']
            # The real Tart child must be able to take the config lock itself.
            probe = real_run([sys.executable, '-c',
                'import fcntl,sys; f=open(sys.argv[1], "r+"); fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)',
                str(target / 'config.json')], capture_output=True)
            assert probe.returncode == 0, probe.stderr
            assert 'LANG=en_US.UTF-8' in argv and 'HOME=/declared/home' in argv
            assert 'PATH=/declared/bin' in argv and 'TART_NO_AUTO_PRUNE=1' in argv
            if condition == 'delete-failed':
                code = 1
            else:
                shutil.rmtree(target)
        else:
            pytest.fail('Unexpected command')
        return subprocess.CompletedProcess(argv, code, out, b'')
    monkeypatch.setattr(owner.subprocess, 'run', run)
    if condition == 'stopped':
        owner.main()
        assert not target.exists()
    else:
        with pytest.raises((AssertionError, RuntimeError)):
            owner.main()
        assert target.exists()
    record = json.loads(receipt.read_text())
    assert record['status'] == ('complete' if condition == 'stopped' else 'failed')
    assert sibling.is_dir()
    if condition in ('running', 'holder'):
        assert not any('delete' in argv for argv in calls)
