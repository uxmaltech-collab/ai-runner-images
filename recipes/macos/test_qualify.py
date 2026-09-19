"""Qualification lifecycle regression tests; no native operations are performed."""
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('qualification_test', Path(__file__).with_name('qualify.py'))
qualification = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qualification)
ROOT = Path(__file__).resolve().parents[2]


def setup(tmp_path, monkeypatch, failure=None, artifact_status='started'):
    parent = tmp_path / 'parent'
    parent.mkdir()
    for name in ('config.json', 'nvram.bin', 'disk.img'):
        (parent / name).write_bytes(name.encode())
    artifact = tmp_path / 'ARTIFACT.json'
    artifact.write_text(json.dumps({'status': artifact_status, 'artifact_state': 'stopped-and-verified',
        'local_image': str(parent), 'image_manifest_sha256': 'a' * 64, 'recipe_commit': 'b' * 40,
        'tuple': {'disk.img': {'bytes': 140000000000}}}))
    binding = tmp_path / 'binding.json'
    binding.write_text(json.dumps({'tart_home': str(tmp_path), 'cpu': 4, 'memory_mib': 8192}))
    work = tmp_path / 'qualification'
    child = tmp_path / 'vms/parent-qualification'
    calls = []
    monkeypatch.setattr(qualification.subprocess, 'check_output',
        lambda command, **kw: 'c' * 40 + '\n' if 'rev-parse' in command else b'')
    def prepare(command, **kw):
        destination = Path(command[command.index('--output') + 1])
        destination.mkdir()
        (destination / 'MODULES.json').write_text('{}')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(qualification.subprocess, 'run', prepare)
    monkeypatch.setattr(qualification.time, 'sleep', lambda seconds: None)
    class FakeOwner:
        def __init__(self, *args): pass
        def op(self, name, operation, *args):
            calls.append(name)
            if name == failure:
                raise RuntimeError('original ' + name + ' failure')
            if operation == 'clone':
                child.mkdir(parents=True)
            if operation == 'delete':
                shutil.rmtree(child)
            value = {'operation': operation, 'status': 'complete'}
            (work / (name + '.json')).write_text(json.dumps(value))
            return value
        def execute(self, name, *args, **kwargs):
            calls.append(name)
            if name == failure:
                raise RuntimeError('original ' + name + ' failure')
            if failure == 'parent-drift' and name == 'lint':
                (parent / 'disk.img').write_bytes(b'changed')
            answer = {'status': 'passed'}
            if name == 'prepare':
                answer = {'status': 'session-prepared', 'reboot_required': True}
            elif name.startswith('status-'):
                answer = {'status': 'starting' if name == 'status-1' else 'ready'}
            path = work / (name + '.stdout')
            path.write_text(json.dumps(answer))
            return path
    monkeypatch.setattr(qualification, 'Owner', FakeOwner)
    def run():
        return qualification.qualify(artifact, work, ROOT, binding, tmp_path, source_kind='consumer')
    return run, calls, work, child, artifact


@pytest.mark.parametrize('artifact_status', ['started', 'passed'])
def test_sealed_artifact_runs_session_lint_and_owned_cleanup(tmp_path, monkeypatch, artifact_status):
    run, calls, work, child, _ = setup(tmp_path, monkeypatch, artifact_status=artifact_status)
    result = run()
    assert calls == ['clone', 'boot-01', 'stage', 'configure', 'prepare', 'session-stop', 'boot-02',
                     'status-1', 'status-2', 'lint', 'result', 'export-lint', 'cleanup-stop', 'cleanup-delete']
    assert result['status'] == 'passed' and not child.exists()
    assert result['cleanup']['sealed_parent_preserved']
    assert Path(result['cleanup']['owner_receipt']['path']) == work / 'cleanup-delete.json'


def test_lint_failure_retains_error_and_still_stops_and_deletes_child(tmp_path, monkeypatch):
    run, calls, work, child, _ = setup(tmp_path, monkeypatch, failure='lint')
    with pytest.raises(RuntimeError, match='original lint failure'):
        run()
    result = json.loads((work / 'QUALIFICATION-RESULT.json').read_text())
    assert result['status'] == 'failed' and result['error'] == 'original lint failure'
    assert calls[-3:] == ['export-lint', 'cleanup-stop', 'cleanup-delete']
    assert not child.exists() and result['cleanup']['sealed_parent_preserved']


@pytest.mark.parametrize('failure', ['cleanup-stop', 'cleanup-delete'])
def test_cleanup_failure_is_durable_and_cannot_pass(tmp_path, monkeypatch, failure):
    run, calls, work, child, _ = setup(tmp_path, monkeypatch, failure=failure)
    with pytest.raises(RuntimeError, match='original ' + failure + ' failure'):
        run()
    result = json.loads((work / 'QUALIFICATION-RESULT.json').read_text())
    assert result['status'] == 'cleanup-unconfirmed' and child.exists()
    if failure == 'cleanup-stop':
        assert 'cleanup-delete' not in calls


def test_parent_mutation_cannot_pass_qualification(tmp_path, monkeypatch):
    run, _, work, child, _ = setup(tmp_path, monkeypatch, failure='parent-drift')
    with pytest.raises(RuntimeError, match='preservation unconfirmed'):
        run()
    result = json.loads((work / 'QUALIFICATION-RESULT.json').read_text())
    assert result['status'] == 'cleanup-unconfirmed'
    assert result['cleanup']['sealed_parent_preserved'] is False and not child.exists()


def test_status_alone_does_not_establish_a_sealed_artifact(tmp_path, monkeypatch):
    run, calls, work, _, artifact = setup(tmp_path, monkeypatch)
    value = json.loads(artifact.read_text())
    value.pop('artifact_state')
    value['status'] = 'stopped-and-verified'
    artifact.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='finalized'):
        run()
    assert calls == [] and not work.exists()
