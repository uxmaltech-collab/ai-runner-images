"""Cross-recipe contracts that previously drifted from their installers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
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


def harness_pins(claude, codex, companion, grok, schema='collab.harness-pins/v2'):
    """A collab.harness-pins/v2 fixture; its versions are not real harness releases."""
    return f'''# Fixture adopted harness pins.
schema: {schema}
harnesses:
  claude:
    version: "9.8.1"
    sha256:
      darwin-arm64: {claude}
  codex:
    version: "9.8.2"
    sha256:
      darwin-arm64: {codex}
    companions:
      codex-code-mode-host:
        darwin-arm64: {companion}
  grok:
    version: "9.8.3"
    sha256:
      linux-amd64: {'b' * 64}
      linux-arm64: {'c' * 64}
      darwin-arm64: {grok}
'''


def test_full_flutter_envelopes_include_transfer_and_all_inner_deadlines():
    flutter = load('recipes/flutter-dart/install.py')
    pins = json.loads((ROOT / 'recipes/flutter-dart/pins.json').read_text())
    # The stage budget follows the actual payload size; the SDK archive alone sets this floor.
    payload_bytes = pins['archive']['bytes']
    assert payload_bytes > 2_200_000_000
    assert budgets.stage_budget(payload_bytes) > 1150
    envelope = budgets.install_budget('macos-flutter', 'macos-xcode-maestro')
    assert envelope['component_seconds']['flutter'] > sum(flutter.STEP_TIMEOUT_SECONDS.values())
    assert envelope['install_seconds'] > sum(envelope['component_seconds'].values())
    assert envelope['install_seconds'] > 3000
    assert budgets.install_budget('macos-flutter', 'flutter-dart-ios')['install_seconds'] == 600
    assert budgets.install_budget('macos-ios', 'shared-agent-build')['component_seconds'] == {'swiftlint': 300}


def test_payload_stages_the_adopted_harness_pins_and_their_versioned_input_names(tmp_path):
    document = tmp_path / 'pack/compatibility/harness-pins.yaml'
    document.parent.mkdir(parents=True)
    document.write_text(harness_pins(*['a' * 64] * 4))
    artifact = tmp_path / 'source.bin'
    artifact.write_bytes(b'locked artifact fixture')
    work = tmp_path / 'work'
    work.mkdir()
    archive = build.payload(ROOT, work, {name: str(artifact) for name in ('codex', 'codex_companion', 'claude', 'grok')},
                            str(document))
    with tarfile.open(archive) as package:
        names = package.getnames()
        staged = package.extractfile('recipes/agent-build/harness-pins.yaml').read()
    assert staged == document.read_bytes()
    assert 'recipes/agent-build/pins.json' not in names
    assert {name for name in names if name.startswith('artifacts/')} == {
        'artifacts/codex', 'artifacts/codex-code-mode-host',
        'artifacts/claude-9.8.1-darwin-arm64', 'artifacts/grok-9.8.3-macos-aarch64'}


def test_installer_verifies_the_adopted_digests_and_refuses_other_documents(tmp_path):
    agents = load('recipes/agent-build/install.py')
    payloads = tmp_path / 'payloads'
    payloads.mkdir()
    files = {}
    for name in ('claude-9.8.1-darwin-arm64', 'codex', 'codex-code-mode-host', 'grok-9.8.3-macos-aarch64'):
        (payloads / name).write_bytes(name.encode())
        files[name] = hashlib.sha256(name.encode()).hexdigest()
    digests = [files['claude-9.8.1-darwin-arm64'], files['codex'], files['codex-code-mode-host'],
               files['grok-9.8.3-macos-aarch64']]
    def verify_inputs(text, receipt):
        document = tmp_path / (receipt + '.yaml')
        document.write_text(text)
        return subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'recipes/agent-build/install.py'),
            '--harness-pins', str(document), '--artifacts', str(payloads),
            '--codex-binary', str(payloads / 'codex'), '--codex-companion', str(payloads / 'codex-code-mode-host'),
            '--receipt', str(tmp_path / (receipt + '.json')), '--verify-inputs-only'], capture_output=True, text=True)
    verified = verify_inputs(harness_pins(*digests), 'verified')
    assert verified.returncode == 0, verified.stderr
    receipt = json.loads((tmp_path / 'verified.json').read_text())
    assert receipt['installed'] is False and receipt['harness_pins_schema'] == 'collab.harness-pins/v2'
    assert receipt['versions'] == {'codex': '9.8.2', 'claude': '9.8.1', 'grok': '9.8.3'}
    assert sorted(row['sha256'] for row in receipt['source_files']) == sorted(digests)
    tampered = verify_inputs(harness_pins('d' * 64, *digests[1:]), 'tampered')
    assert tampered.returncode != 0 and 'digest mismatch' in tampered.stderr
    assert not (tmp_path / 'tampered.json').exists()
    valid = harness_pins(*digests)
    for text, message in [
            (harness_pins(*digests, schema='collab.harness-pins/v1'), 'not a collab.harness-pins/v2 document'),
            (valid.replace('      codex-code-mode-host:\n        darwin-arm64', '      codex-code-mode-host:\n        darwin-amd64'),
             'lacks the darwin-arm64 digest of the codex companion'),
            (valid.replace('      darwin-arm64: ' + digests[3], ''), 'lacks the darwin-arm64 digest of grok'),
            (valid.replace('version: "9.8.1"', 'version: latest'), 'no exact version of claude'),
            (valid + 'extra: {flow: style}\n', 'not a plain block-mapping entry')]:
        document = tmp_path / 'refused.yaml'
        document.write_text(text)
        with pytest.raises(ValueError, match=message):
            agents.read_pins(document)


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
