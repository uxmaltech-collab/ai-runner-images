"""Entrypoint binds committed recipes and preserves failed build evidence."""
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest

SPEC = importlib.util.spec_from_file_location('build_images', Path(__file__).with_name('build-images.py'))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / 'source'; root.mkdir()
    (root / 'backend.py').write_text("def build(inputs, work, root, commit, *, profile):\n    raise ValueError('fixture failure')\n")
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid', '-C', str(root),
                    'commit', '-qm', 'Fixture'], check=True)
    monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(module, 'PROFILES', {'android': ('Linux', 'backend.py')})
    monkeypatch.setattr(module.platform, 'system', lambda: 'Linux')
    config = tmp_path / 'inputs.json'
    config.write_text(json.dumps({'schema_version': 1, 'profile': 'android', 'inputs': {}}))
    work = tmp_path / 'build'
    return root, config, work

def arguments(source, operation='build'):
    root, config, work = source
    return [operation, '--profile', 'android', '--inputs', str(config), '--work-dir', str(work)]

def test_plan_does_not_build_or_create_work(source, capsys):
    assert module.main(arguments(source, 'plan')) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan['source_clean'] and not plan['runtime_admission']
    assert len(plan['source_commit']) == 40
    assert not source[2].exists()

def test_backend_failure_is_recorded_without_replacing_original(source):
    assert module.main(arguments(source)) == 1
    assert json.loads((source[2] / 'RESULT.json').read_text())['reason'] == 'fixture failure'
    first = (source[2] / 'RESULT.json').read_bytes()
    assert module.main(arguments(source)) == 1
    assert (source[2] / 'RESULT.json').read_bytes() == first

def test_dirty_recipe_cannot_be_attributed_to_commit(source):
    (source[0] / 'backend.py').write_text('changed source')
    assert module.main(arguments(source)) == 1
    assert not source[2].exists()

def test_wrong_platform_cannot_mutate(source, monkeypatch):
    monkeypatch.setattr(module.platform, 'system', lambda: 'Darwin')
    assert module.main(arguments(source)) == 1
    assert not source[2].exists()

@pytest.mark.parametrize('document', [[], {'schema_version':1, 'profile':'macos-ios', 'inputs':{}},
    {'schema_version':1, 'profile':'android','inputs':{},'command':'ignored shell command'}])
def test_invalid_input_does_not_start(source, document):
    source[1].write_text(json.dumps(document))
    assert module.main(arguments(source)) == 1
    assert not source[2].exists()
