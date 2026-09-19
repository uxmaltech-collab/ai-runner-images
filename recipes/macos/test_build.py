import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('macos_build_test', Path(__file__).with_name('build.py'))
backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backend)
COMMIT = 'a' * 40


def inputs(tmp_path):
    parent = tmp_path / 'parent'
    parent.mkdir()
    pins = {}
    for name in ('config.json', 'nvram.bin', 'disk.img'):
        file = parent / name
        file.write_bytes(name.encode())
        pins[name] = {'bytes': file.stat().st_size, 'sha256': backend.sha(file)}
    manifest = tmp_path / 'parent.json'
    manifest.write_text(json.dumps({'files': pins}))
    binding = tmp_path / 'binding.json'
    binding.write_text(json.dumps({'tart_home': str(tmp_path)}))
    artifact = tmp_path / 'swiftlint.zip'
    artifact.write_bytes(b'fixture')
    return {'schema_version': 1, 'name': 'fixture-ios', 'binding': str(binding),
            'parent': {'directory': str(parent), 'manifest': str(manifest),
                       'sha256': backend.sha(manifest), 'layer': 'shared-agent-build'},
            'artifacts': {'swiftlint': str(artifact)},
            'qualification': {'source_checkout': str(tmp_path), 'source_kind': 'consumer'}}


def fake_host(monkeypatch, tmp_path, fail=False):
    calls = []
    monkeypatch.setattr(backend.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(backend.platform, 'machine', lambda: 'arm64')
    monkeypatch.setattr(backend.subprocess, 'check_output',
        lambda command, **kw: COMMIT + '\n' if 'rev-parse' in command else b'')
    monkeypatch.setattr(backend, 'payload', lambda *args: tmp_path / 'unused-payload.tar')
    monkeypatch.setattr(backend, 'qualify_artifact',
        lambda *args: {'status': 'passed', 'cleanup': {'owned_child_absent': True}})
    class FakeOwner:
        def __init__(self, *args): pass
        def op(self, name, operation, *args):
            calls.append((name, operation))
            if operation == 'seal':
                path = tmp_path / 'sealed.json'
                path.write_text('{}')
                return {'manifest_path': str(path), 'manifest_sha256': backend.sha(path), 'manifest': {'files': {}}}
            return {'status': 'complete'}
        def execute(self, name, *args, **kwargs):
            calls.append((name, 'exec'))
            if fail and name == 'install':
                raise RuntimeError('retained recipe failure')
            path = tmp_path / (name + '.output')
            path.write_text('{}')
            return path
    monkeypatch.setattr(backend, 'Owner', FakeOwner)
    return calls


def test_stopped_tuple_is_sealed_only_after_export_and_normal_shutdown(tmp_path, monkeypatch):
    declaration = inputs(tmp_path)
    calls = fake_host(monkeypatch, tmp_path)
    result = backend.build(declaration, tmp_path / 'work', tmp_path, COMMIT, profile='macos-ios')
    assert [x[0] for x in calls] == ['clone', 'boot', 'stage', 'install', 'export', 'remove-stage', 'stop', 'seal']
    assert result['runtime_admission'] is False
    assert result['distribution'] == 'local-only'
    assert result['recipe_commit'] == COMMIT and result['physical_parent'] == declaration['parent']
    assert result['status'] == 'passed' and result['artifact_state'] == 'stopped-and-verified'


def test_install_failure_preserves_error_and_stops_owned_builder_without_sealing(tmp_path, monkeypatch):
    declaration = inputs(tmp_path)
    calls = fake_host(monkeypatch, tmp_path, fail=True)
    with pytest.raises(RuntimeError, match='retained recipe failure'):
        backend.build(declaration, tmp_path / 'work', tmp_path, COMMIT, profile='macos-ios')
    result = json.loads((tmp_path / 'work/BUILD-RESULT.json').read_text())
    assert result['failed_builder_stopped'] and result['error'] == 'retained recipe failure'
    assert calls[-1] == ('failure-stop', 'stop')
    assert not any(x[1] == 'seal' for x in calls)


def test_parent_drift_never_starts_tart(tmp_path, monkeypatch):
    declaration = inputs(tmp_path)
    (tmp_path / 'parent/disk.img').write_bytes(b'changed')
    calls = fake_host(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match='Parent tuple'):
        backend.build(declaration, tmp_path / 'work', tmp_path, COMMIT, profile='macos-ios')
    assert not calls


def test_existing_work_is_not_overwritten(tmp_path, monkeypatch):
    declaration = inputs(tmp_path)
    calls = fake_host(monkeypatch, tmp_path)
    work = tmp_path / 'work'
    work.mkdir()
    (work / 'original').write_text('retained')
    with pytest.raises(FileExistsError):
        backend.build(declaration, work, tmp_path, COMMIT, profile='macos-ios')
    assert not calls and (work / 'original').read_text() == 'retained'


def test_canonical_front_end_plan_handoff(tmp_path, monkeypatch):
    declaration = inputs(tmp_path)
    calls = fake_host(monkeypatch, tmp_path)
    work = tmp_path / 'work'
    work.mkdir()
    plan = {'profile': 'macos-ios', 'source_commit': COMMIT, 'source_clean': True,
            'backend': 'recipes/macos/build.py', 'work_dir': str(work.resolve())}
    (work / 'PLAN.json').write_text(json.dumps(plan))
    result = backend.build(declaration, work, tmp_path, COMMIT, profile='macos-ios')
    assert result['status'] == 'passed' and calls[-1] == ('seal', 'seal')
    assert json.loads((work / 'PLAN.json').read_text()) == plan


def test_foreign_front_end_plan_never_creates_a_vm(tmp_path, monkeypatch):
    declaration = inputs(tmp_path)
    calls = fake_host(monkeypatch, tmp_path)
    work = tmp_path / 'work'
    work.mkdir()
    (work / 'PLAN.json').write_text(json.dumps({'profile': 'android'}))
    with pytest.raises(ValueError, match='Front-end plan'):
        backend.build(declaration, work, tmp_path, COMMIT, profile='macos-ios')
    assert not calls


def test_qualification_failure_cannot_be_reported_as_successful_build(tmp_path, monkeypatch):
    declaration = inputs(tmp_path)
    fake_host(monkeypatch, tmp_path)
    monkeypatch.setattr(backend, 'qualify_artifact', lambda *args: {'status': 'failed'})
    with pytest.raises(ValueError, match='qualification did not pass'):
        backend.build(declaration, tmp_path / 'work', tmp_path, COMMIT, profile='macos-ios')
    failed = json.loads((tmp_path / 'work/BUILD-RESULT.json').read_text())
    assert failed['status'] == 'failed' and not failed['runtime_admission']
    assert (tmp_path / 'work/ARTIFACT.json').exists()


def test_flutter_from_base_requires_all_engines_and_flutter_archive(tmp_path):
    declaration = inputs(tmp_path)
    declaration['parent']['layer'] = 'macos-xcode-maestro'
    with pytest.raises(ValueError, match='offline artifacts'):
        backend.validate(declaration, 'macos-flutter')
    for name in ('codex', 'codex_companion', 'claude', 'grok', 'flutter'):
        declaration['artifacts'][name] = '/approved/' + name
    assert len(backend.validate(declaration, 'macos-flutter')) == 6


def test_flutter_parent_reuses_locked_sdk_without_downloading_or_reinstalling(tmp_path):
    declaration = inputs(tmp_path)
    declaration['parent']['layer'] = 'flutter-dart-ios'
    assert backend.validate(declaration, 'macos-flutter') == {'swiftlint'}
    with pytest.raises(ValueError, match='iOS base'):
        backend.validate(declaration, 'macos-ios')
