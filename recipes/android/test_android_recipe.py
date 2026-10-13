"""Exercise ownership, failure propagation and cleanup without starting a VM."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace
import zipfile
import xml.etree.ElementTree as ET

import pytest

IMAGE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'android_emulator', IMAGE / 'scripts' / 'runner-android-emulator.py')
emulator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emulator)
INSTALL_SPEC = importlib.util.spec_from_file_location('android_install', IMAGE / 'scripts' / 'install-toolchain.py')
installer = importlib.util.module_from_spec(INSTALL_SPEC)
INSTALL_SPEC.loader.exec_module(installer)
ENTRY_SPEC = importlib.util.spec_from_file_location('android_entrypoint', IMAGE / 'scripts' / 'entrypoint-android.py')
entrypoint = importlib.util.module_from_spec(ENTRY_SPEC)
ENTRY_SPEC.loader.exec_module(entrypoint)


@pytest.fixture
def fake_tools(tmp_path, monkeypatch):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    scripts = {
        'avdmanager': "import sys\nsys.stdin.read()\n",
        'adb': """import os, sys
if 'get-state' in sys.argv:
    sys.exit(0 if os.environ.get('FAKE_EXISTING') else 1)
if 'getprop' in sys.argv:
    print('0' if os.environ.get('FAKE_BOOT_TIMEOUT') else '1')
if 'settings' in sys.argv and os.environ.get('FAKE_SETTING_FAILURE'):
    sys.exit(1)
""",
        'emulator': """import json, os, signal, time
from pathlib import Path
def stop(signum, frame):
    Path(os.environ['FAKE_STOP_RECEIPT']).write_text(json.dumps({
        'state_exists_at_stop': Path(os.environ['ANDROID_AVD_HOME']).is_dir(),
        'state_path': os.environ['ANDROID_AVD_HOME'],
        'pid': os.getpid(),
    }))
    raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
while True:
    time.sleep(0.02)
""",
    }
    for name, source in scripts.items():
        path = bin_dir / name
        path.write_text(f'#!{sys.executable}\n' + source)
        path.chmod(0o755)
    monkeypatch.setenv('PATH', str(bin_dir) + os.pathsep + os.environ['PATH'])
    monkeypatch.setenv('FAKE_STOP_RECEIPT', str(tmp_path / 'stop.json'))
    return tmp_path


@pytest.mark.parametrize('exit_code', [0, 37])
def test_command_exit_and_cleanup_are_preserved(fake_tools, exit_code):
    logs = fake_tools / 'logs'
    result = fake_tools / 'child.json'
    code = "import json,os,time;time.sleep(.1);json.dump({k:os.environ[k] for k in ['ANDROID_SERIAL','RUNNER_ANDROID_EMULATOR_OWNED','ANDROID_USER_HOME']},open(os.environ['FAKE_CHILD'],'w'));raise SystemExit(%d)" % exit_code
    os.environ['FAKE_CHILD'] = str(result)
    try:
        assert emulator.execute([sys.executable, '-c', code], logs, boot_timeout=1) == exit_code
    finally:
        del os.environ['FAKE_CHILD']
    receipt = json.loads((logs / 'emulator-result.json').read_text())
    assert receipt['command_exit_code'] == exit_code
    assert receipt['booted'] and receipt['cleanup_confirmed']
    child = json.loads(result.read_text())
    assert child['ANDROID_SERIAL'] == 'emulator-5554'
    assert child['RUNNER_ANDROID_EMULATOR_OWNED'] == '1'
    stopped = json.loads((fake_tools / 'stop.json').read_text())
    assert stopped['state_exists_at_stop']
    assert not Path(stopped['state_path']).exists()
    with pytest.raises(ProcessLookupError):
        os.kill(stopped['pid'], 0)


def test_boot_timeout_cleans_owned_vm_and_does_not_run_command(fake_tools, monkeypatch):
    monkeypatch.setenv('FAKE_BOOT_TIMEOUT', '1')
    result = fake_tools / 'must-not-exist'
    logs = fake_tools / 'logs'
    assert emulator.execute([sys.executable, '-c', f'open({str(result)!r},"w").close()'],
                            logs, boot_timeout=0.05) == 1
    assert not result.exists()
    receipt = json.loads((logs / 'emulator-result.json').read_text())
    assert not receipt['booted']
    assert receipt['command_exit_code'] is None
    assert receipt['cleanup_confirmed']
    assert (fake_tools / 'stop.json').exists()


def test_existing_device_is_not_adopted_or_stopped(fake_tools, monkeypatch):
    monkeypatch.setenv('FAKE_EXISTING', '1')
    logs = fake_tools / 'logs'
    assert emulator.execute(['must-not-start'], logs, boot_timeout=1) == 1
    assert not (fake_tools / 'stop.json').exists()
    assert not (logs / 'emulator.log').exists()
    receipt = json.loads((logs / 'emulator-result.json').read_text())
    assert 'refusing to adopt' in receipt['error']


def test_optional_settings_failure_is_a_warning(fake_tools, monkeypatch, capsys):
    monkeypatch.setenv('FAKE_SETTING_FAILURE', '1')
    assert emulator.execute([sys.executable, '-c', 'import time;time.sleep(.1)'],
                            fake_tools / 'logs', boot_timeout=1) == 0
    assert 'WARNING: could not set' in capsys.readouterr().err


def test_existing_receipt_is_not_replaced(fake_tools):
    logs = fake_tools / 'logs'
    logs.mkdir()
    receipt = logs / 'emulator-result.json'
    receipt.write_text('original')
    with pytest.raises(RuntimeError, match='receipt already exists'):
        emulator.execute(['must-not-start'], logs)
    assert receipt.read_text() == 'original'


@pytest.fixture
def tool_archive(tmp_path):
    archive = tmp_path / 'tool.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        member = zipfile.ZipInfo('tool/bin/tool')
        member.external_attr = 0o100755 << 16
        output.writestr(member, '#!/bin/sh\nprintf installed')
    item = {'name': 'tool', 'version': '1', 'url': archive.as_uri(),
            'size': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'archive_root': 'tool', 'destination': str(tmp_path / 'installed')}
    return archive, item


def test_installer_downloads_verifies_and_preserves_executable(tool_archive):
    archive, item = tool_archive
    installer.install({'archives': [item]})
    binary = Path(item['destination']) / 'bin/tool'
    assert binary.read_text() == '#!/bin/sh\nprintf installed'
    assert os.access(binary, os.X_OK)


def test_verified_cache_avoids_network(tool_archive, monkeypatch):
    archive, item = tool_archive
    monkeypatch.setattr(installer, 'urlopen', lambda *a, **k: pytest.fail('cache must avoid network'))
    installer.install({'archives': [item]}, archive.parent)
    assert (Path(item['destination']) / 'bin/tool').is_file()


@pytest.mark.parametrize('corruption', ['same-size', 'truncated', 'oversize'])
def test_corrupt_cache_cannot_extract_or_fall_back_to_network(tool_archive, monkeypatch, corruption):
    archive, item = tool_archive
    data = archive.read_bytes()
    data = b'X' + data[1:] if corruption == 'same-size' else data[:-1] if corruption == 'truncated' else data + b'X'
    archive.write_bytes(data)
    monkeypatch.setattr(installer, 'urlopen', lambda *a, **k: pytest.fail('invalid cache must not be hidden'))
    with pytest.raises(RuntimeError, match='Archive .* mismatch'):
        installer.install({'archives': [item]}, archive.parent)
    assert not Path(item['destination']).exists()


def test_installer_does_not_replace_existing_directory(tool_archive):
    archive, item = tool_archive
    destination = Path(item['destination'])
    destination.mkdir()
    (destination / 'existing').write_text('original')
    with pytest.raises(RuntimeError, match='Refusing to replace'):
        installer.install({'archives': [item]}, archive.parent)
    assert (destination / 'existing').read_text() == 'original'


@pytest.fixture
def bootstrap_identity(monkeypatch):
    monkeypatch.setattr(entrypoint.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(entrypoint.pwd, 'getpwnam', lambda _: SimpleNamespace(pw_uid=1001, pw_gid=1001))
    monkeypatch.setattr(entrypoint.os, 'getgrouplist', lambda *_: [1001, 1002])
    monkeypatch.setattr(entrypoint.Path, 'stat', lambda _: SimpleNamespace(st_mode=stat.S_IFCHR, st_gid=994))


def test_bootstrap_adds_device_group_and_drops_before_inherited_entrypoint(bootstrap_identity):
    command = entrypoint.entrypoint_argv(['job-argument'])
    assert command == ['/usr/bin/setpriv', '--reuid', '1001', '--regid', '1001',
                       '--groups', '994,1001,1002', '--no-new-privs', '--', '/entrypoint.sh', 'job-argument']


def test_bootstrap_rejects_non_device_path(bootstrap_identity, monkeypatch):
    monkeypatch.setattr(entrypoint.Path, 'stat', lambda _: SimpleNamespace(st_mode=stat.S_IFREG, st_gid=994))
    with pytest.raises(RuntimeError, match='character device'):
        entrypoint.entrypoint_argv([])


def test_bootstrap_resolve_without_kvm(bootstrap_identity, monkeypatch):
    def absent(_):
        raise FileNotFoundError
    monkeypatch.setattr(entrypoint.Path, 'stat', absent)
    command = entrypoint.entrypoint_argv([])
    assert command[command.index('--groups') + 1] == '1001,1002'


def test_bootstrap_rejects_unprivileged_initial_identity(bootstrap_identity, monkeypatch):
    monkeypatch.setattr(entrypoint.os, 'geteuid', lambda: 1001)
    with pytest.raises(RuntimeError, match='must start as root'):
        entrypoint.entrypoint_argv([])


@pytest.mark.skipif(os.geteuid() != 0, reason='real credential drop requires local root')
def test_actual_drop_preserves_no_new_privileges(bootstrap_identity):
    command = entrypoint.entrypoint_argv([])
    command = command[:command.index('/entrypoint.sh')] + [
        '/usr/bin/python3', '-I', '-c',
        "import json,os;print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'status':open('/proc/self/status').read()}))"]
    result = subprocess.run(['/usr/bin/setpriv', '--no-new-privs', '--', *command],
                            capture_output=True, text=True, timeout=10, check=True)
    observed = json.loads(result.stdout)
    assert observed['uid'] == observed['gid'] == 1001
    assert observed['groups'] == [994, 1001, 1002]
    assert 'NoNewPrivs:\t1' in observed['status']


def test_emulator_registration_matches_verified_archive_pin():
    lock = json.loads((IMAGE / 'toolchain-lock.json').read_text())
    archive = next(item for item in lock['archives'] if item['name'] == 'emulator')
    package = ET.parse(IMAGE / 'emulator-package.xml').getroot().find('localPackage')
    assert package.get('path') == 'emulator'
    assert '.'.join(node.text for node in package.find('revision')) == archive['version']
    assert package.find('type-details').get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ns3:genericDetailsType'


def test_compile_and_sdk36_test_java_are_distinct_locked_runtimes():
    lock = json.loads((IMAGE / 'toolchain-lock.json').read_text())
    archives = {item['name']: item for item in lock['archives']}
    compile_java = next(item for item in archives.values() if item['destination'] == '/opt/java')
    test_java = archives['jdk-test']
    assert compile_java['version'].startswith('17.')
    assert test_java['version'] == '21.0.10+7'
    assert test_java['destination'] == '/usr/lib/jvm/temurin-21'
    assert test_java['sha256'] == 'ea3b9bd464d6dd253e9a7accf59f7ccd2a36e4aa69640b7251e3370caef896a4'
    dockerfile = (IMAGE / 'Dockerfile').read_text()
    assert 'JAVA_HOME=/opt/java' in dockerfile
    assert 'JAVA21_HOME=/usr/lib/jvm/temurin-21' in dockerfile
    assert '/opt/java /usr/lib/jvm/temurin-21 /opt/maestro' in dockerfile
    probe = (IMAGE / 'scripts/runner-android-stack-probe.sh').read_text()
    assert '"$JAVA21_HOME/bin/java" -version' in probe


def tool_seed(root, **gradle):
    """A seed as a rollout leaves it: the manifest, an unpacked distribution and a dependency cache."""
    (root / 'gradle' / 'distribution' / 'gradle-8.13' / 'bin').mkdir(parents=True)
    (root / 'gradle' / 'distribution' / 'gradle-8.13' / 'bin' / 'gradle').write_text('#!/bin/sh\n')
    (root / 'gradle' / 'ro-dep-cache' / 'modules-2').mkdir(parents=True)
    (root / 'manifest.json').write_text(json.dumps({'gradle': {
        'wrapper_directory': 'gradle-8.13-bin/5xuhj0ry160q40clulazy9h7d', 'archive_name': 'gradle-8.13-bin.zip',
        'distribution': 'gradle/distribution/gradle-8.13', 'ro_dep_cache': 'gradle/ro-dep-cache', **gradle}}))
    return root


def test_a_tool_seed_gives_the_wrapper_a_writable_home_that_points_at_the_read_only_seed(tmp_path):
    seed, home = tool_seed(tmp_path / 'seed'), tmp_path / 'tmp' / 'gradle-home'
    home.parent.mkdir()
    environment = entrypoint.gradle_seed_environment(seed, home=home, owner=(os.getuid(), os.getgid()))
    assert environment == {'GRADLE_USER_HOME': str(home), 'GRADLE_RO_DEP_CACHE': str(seed / 'gradle' / 'ro-dep-cache')}
    kept = home / 'wrapper' / 'dists' / 'gradle-8.13-bin' / '5xuhj0ry160q40clulazy9h7d'
    # What the Gradle wrapper asks before it downloads: its marker and exactly one distribution directory.
    assert (kept / 'gradle-8.13-bin.zip.ok').is_file()
    assert [entry.name for entry in kept.iterdir() if entry.is_dir()] == ['gradle-8.13']
    assert (kept / 'gradle-8.13').resolve() == (seed / 'gradle' / 'distribution' / 'gradle-8.13').resolve()
    assert sorted(path.name for path in home.rglob('*') if path.is_file() and not path.is_symlink()) == ['gradle-8.13-bin.zip.ok']


@pytest.mark.parametrize('broken', [
    {'ro_dep_cache': 'gradle/absent'}, {'distribution': 'gradle/absent'},
    {'wrapper_directory': '../../outside'}, {'archive_name': 'a/b.zip'},
])
def test_a_seed_the_image_cannot_use_changes_nothing_and_says_so(tmp_path, capsys, broken):
    home = tmp_path / 'gradle-home'
    assert entrypoint.gradle_seed_environment(tool_seed(tmp_path / 'seed', **broken), home=home,
                                              owner=(os.getuid(), os.getgid())) == {}
    assert 'tool seed not used' in capsys.readouterr().err and not home.exists()
    assert entrypoint.gradle_seed_environment(tmp_path / 'no-seed', home=home) == {}
