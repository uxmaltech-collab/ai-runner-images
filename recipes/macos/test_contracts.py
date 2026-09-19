"""Cross-recipe contracts that previously drifted from their installers."""
import importlib.util
import json
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from recipes.macos import budgets, build, host, stage_payload


def load(relative):
    spec = importlib.util.spec_from_file_location('recipe_contract_test', ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_flutter_envelopes_include_transfer_and_all_inner_deadlines():
    flutter = load('recipes/flutter-dart/install.py')
    pins = json.loads((ROOT / 'recipes/flutter-dart/pins.json').read_text())
    agents = json.loads((ROOT / 'recipes/agent-build/pins.json').read_text())
    payload_bytes = pins['archive']['bytes'] + sum(pin['bytes'] for pin in
        [agents['codex']['binary'], agents['codex']['companion'], agents['claude'], agents['grok']])
    assert payload_bytes > 2_800_000_000
    assert budgets.stage_budget(payload_bytes) > 1400
    envelope = budgets.install_budget('macos-flutter', 'macos-xcode-maestro')
    assert envelope['component_seconds']['flutter'] > sum(flutter.STEP_TIMEOUT_SECONDS.values())
    assert envelope['install_seconds'] > sum(envelope['component_seconds'].values())
    assert envelope['install_seconds'] > 3000
    assert budgets.install_budget('macos-flutter', 'flutter-dart-ios')['install_seconds'] == 600
    assert budgets.install_budget('macos-ios', 'shared-agent-build')['component_seconds'] == {'swiftlint': 300}


def test_payload_uses_installer_pin_filenames(tmp_path):
    root = tmp_path / 'source'
    recipe = root / 'recipes/agent-build'
    recipe.mkdir(parents=True)
    pins = {'codex': {'binary': {'installed_name': 'codex-next'}, 'companion': {'installed_name': 'host-next'}},
            'claude': {'file': 'claude-next'}, 'grok': {'file': 'grok-next'}}
    (recipe / 'pins.json').write_text(json.dumps(pins))
    artifact = tmp_path / 'source.bin'
    artifact.write_bytes(b'locked artifact fixture')
    work = tmp_path / 'work'
    work.mkdir()
    archive = build.payload(root, work, {name: str(artifact) for name in ('codex', 'codex_companion', 'claude', 'grok')})
    with tarfile.open(archive) as package:
        names = package.getnames()
    assert {name for name in names if name.startswith('artifacts/')} == {
        'artifacts/codex-next', 'artifacts/host-next', 'artifacts/claude-next', 'artifacts/grok-next'}


def test_installers_are_the_launcher_and_layout_authority():
    swift = load('recipes/macos-xcode-maestro/swiftlint/install.py')
    prefix, bin_dir = swift.layout('neutral', {'version': 'future-fixture'})
    assert str(prefix).endswith('/future-fixture')
    assert swift.launcher_bytes(prefix) == f'#!/bin/sh\nexec {prefix}/swiftlint "$@"\n'.encode()
    agents = load('recipes/agent-build/install.py')
    assert b'DISABLE_AUTOUPDATER=1' in agents.launcher_bytes('claude')
    assert b'DISABLE_AUTOUPDATER' not in agents.launcher_bytes('codex')


def test_shared_pack_and_guest_stage_verify_transferred_bytes(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.write_bytes(b'fixture')
    work = tmp_path / 'work'
    work.mkdir()
    archive = host.pack({'recipes/file': source}, work)
    monkeypatch.setattr(stage_payload.os, 'chown', lambda *args: None)
    with archive.open('rb') as stream:
        assert stage_payload.stage(tmp_path / 'guest', stream)['verified_files'] == 1
    source.write_bytes(b'changed')
    with tarfile.open(tmp_path / 'tampered.tar', 'x') as package:
        package.add(source, arcname='recipes/file')
        package.add(work / 'PAYLOAD.json', arcname='PAYLOAD.json')
    with (tmp_path / 'tampered.tar').open('rb') as stream, pytest.raises(ValueError, match='digest mismatch'):
        stage_payload.stage(tmp_path / 'failed-guest', stream)


def test_qualification_config_derives_versions_source_and_fixture_identity(tmp_path, monkeypatch):
    configure = load('recipes/qualification-session/configure-native-tools.py')
    policy = json.loads((ROOT / 'recipes/qualification-session/native-tools-policy.json').read_text())
    policy['session_policy']['runner'] = {'name': 'fixture-runner', 'uid': 777, 'gid': 20, 'home': '/Users/fixture-runner'}
    (tmp_path / 'native-tools-policy.json').write_text(json.dumps(policy))
    (tmp_path / 'MODULES.json').write_text(json.dumps({'source_commit': 'd' * 40}))
    (tmp_path / 'swiftlint').mkdir()
    (tmp_path / 'swiftlint/pins.json').write_text(json.dumps({'version': 'future-version'}))
    (tmp_path / 'qualification-session.py').write_bytes(b'fixture')
    # Tool bytes are host-independent fixtures; no /opt mutation or executable runs.
    monkeypatch.setattr(Path, 'read_bytes', lambda self: b'fixture executable')
    paths = {'python': '/fixture/python', 'java_home': '/fixture/java', 'node_bin': '/fixture/node',
             'developer_dir': '/fixture/Xcode'}
    configure.configure(tmp_path, 'e' * 40, 'fixture@sha256:' + 'a' * 64, {'cpus': 4}, paths)
    config = json.loads((tmp_path / 'qualification.json').read_text())
    command = json.loads((tmp_path / 'commands/swiftlint.json').read_text())
    assert config['session_source_commit'] == 'd' * 40
    assert config['tools']['swiftlint']['version_contains'] == 'future-version'
    assert config['session_policy']['runner']['uid'] == 777
    assert config['guest_user'] == 'fixture-runner'
    assert command['cwd'] == '/Users/fixture-runner'
    assert command['args'][-1] == '/Users/fixture-runner/swiftlint-qualification'
    assert '/fixture/java/bin:/fixture/node:' in config['environment']['PATH']
