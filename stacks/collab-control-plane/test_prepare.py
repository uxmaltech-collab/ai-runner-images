"""Offline context preparation with real, explicitly supplied release artifacts.

COLLAB_TEST_RELEASES names a directory containing base/runners/infra releases.
These are test inputs only; preparing a context does not qualify an image.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('control_plane_prepare', HERE / 'prepare.py')
recipe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recipe)
PYTHON_BASE = 'python@sha256:' + 'a' * 64
RUNNER_BASE = 'runner-tools@sha256:' + 'b' * 64


@pytest.fixture(scope='session')
def releases():
    value = os.environ.get('COLLAB_TEST_RELEASES')
    if not value:
        pytest.skip('Requires explicit COLLAB_TEST_RELEASES with offline release artifacts')
    root = Path(value)
    assert all((root / name / 'release-manifest.json').is_file()
               for name in ('base', 'runners', 'infra'))
    return root


def prepare(releases, output, *, profile='runners', lock=None, python_base=PYTHON_BASE):
    artifacts = releases / profile
    return recipe.prepare(artifacts, lock or artifacts / 'collab-runtime.lock.json',
                          output, python_base, RUNNER_BASE)


@pytest.mark.parametrize('value', [[], None, 'invalid', {'schema': 'collab.runtime-lock/v1'},
                                   {'runtime': []}])
def test_malformed_lock_is_a_typed_rejection_before_context(releases, tmp_path, value):
    lock = tmp_path / 'lock.json'; lock.write_text(json.dumps(value))
    output = tmp_path / 'context'
    with pytest.raises(ValueError):
        prepare(releases, output, lock=lock)
    assert not output.exists()


def test_lock_unknown_fields_are_not_ignored(releases, tmp_path):
    value = json.loads((releases / 'runners/collab-runtime.lock.json').read_text())
    value['unregistered_authority'] = True
    lock = tmp_path / 'lock.json'; lock.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        prepare(releases, tmp_path / 'context', lock=lock)
    assert not (tmp_path / 'context').exists()


@pytest.mark.parametrize('image', [None, 1, [], 'python:3.12', 'python@sha256:' + 'a' * 63])
def test_base_identity_must_be_a_digest_string(releases, tmp_path, image):
    with pytest.raises(ValueError):
        prepare(releases, tmp_path / 'context', python_base=image)
    assert not (tmp_path / 'context').exists()


@pytest.mark.parametrize('profile', ['runners', 'infra'])
def test_real_verified_release_copies_exact_artifacts_and_provider_identity(releases, tmp_path, profile):
    output = tmp_path / 'context'
    receipt = prepare(releases, output, profile=profile)
    original = recipe.verify_release(releases / profile)
    assert recipe.verify_release(output / 'collab-release') == original
    for item in (releases / profile).iterdir():
        assert (output / 'collab-release' / item.name).read_bytes() == item.read_bytes()
    assert receipt['runtime'] == original['runtime']
    assert receipt['release']['profile'] == original['profile']
    assert receipt['release']['providers'] == original['providers']
    for relative, digest in receipt['files'].items():
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == digest
    assert receipt['image_build'] == receipt['image_publication'] == receipt['host_installation'] == 'not-run'
    assert json.loads((output / 'context-receipt.json').read_text()) == receipt


def test_base_only_release_is_rejected_before_context(releases, tmp_path):
    with pytest.raises(ValueError, match='runners provider'):
        prepare(releases, tmp_path / 'context', profile='base')
    assert not (tmp_path / 'context').exists()


@pytest.mark.parametrize('kind', ['directory', 'file', 'dangling-symlink'])
def test_existing_output_is_preserved(releases, tmp_path, kind):
    output = tmp_path / 'context'
    if kind == 'directory':
        output.mkdir(); (output / 'unique').write_bytes(b'preserve')
    elif kind == 'file': output.write_bytes(b'preserve')
    else: output.symlink_to(tmp_path / 'absent')
    with pytest.raises(ValueError, match='new directory'):
        prepare(releases, output)
    if kind == 'directory': assert (output / 'unique').read_bytes() == b'preserve'
    elif kind == 'file': assert output.read_bytes() == b'preserve'
    else: assert output.is_symlink()


def test_copy_drift_does_not_publish_a_context_receipt(releases, tmp_path, monkeypatch):
    output = tmp_path / 'context'
    copyfile = recipe.shutil.copyfile
    def altered_copy(source, target, *args, **kwargs):
        result = copyfile(source, target, *args, **kwargs)
        if Path(target).name == 'install.py':
            with Path(target).open('ab') as stream: stream.write(b'\n# synthetic copy drift\n')
        return result
    monkeypatch.setattr(recipe.shutil, 'copyfile', altered_copy)
    with pytest.raises(ValueError): prepare(releases, output)
    assert not (output / 'context-receipt.json').exists()
    assert (output / 'collab-release/install.py').exists(), 'Preserve partial evidence for inspection'


def test_source_drift_during_copy_does_not_publish_a_context_receipt(releases, tmp_path, monkeypatch):
    source = tmp_path / 'inputs'; shutil.copytree(releases / 'runners', source / 'runners')
    output = tmp_path / 'context'; copyfile = recipe.shutil.copyfile
    def altered_source(path, target, *args, **kwargs):
        if Path(path).name == 'install.py':
            with Path(path).open('ab') as stream: stream.write(b'\n# synthetic source drift\n')
        return copyfile(path, target, *args, **kwargs)
    monkeypatch.setattr(recipe.shutil, 'copyfile', altered_source)
    with pytest.raises(ValueError): prepare(source, output)
    assert not (output / 'context-receipt.json').exists()


def test_docker_command_is_a_module_in_the_verified_provider(releases):
    manifest = recipe.verify_release(releases / 'runners')
    text = (HERE / 'Dockerfile').read_text()
    command = json.loads(next(line[4:] for line in text.splitlines() if line.startswith('CMD ')))
    assert command[:3] == ['/opt/collab/runtime/bin/python', '-I', '-m']
    provider = next(row for row in manifest['providers'] if row['id'] == 'runners')
    with zipfile.ZipFile(releases / 'runners' / provider['artifact']['name']) as wheel:
        assert command[3].replace('.', '/') + '/__main__.py' in wheel.namelist()
    assert 'git openssh-client' in text
    assert 'git --version' in text and 'ssh -V' in text


def test_cli_malformed_lock_has_a_bounded_contract_error(releases, tmp_path):
    lock = tmp_path / 'invalid.json'; lock.write_text('[]')
    output = tmp_path / 'context'
    result = subprocess.run([sys.executable, str(HERE / 'prepare.py'), '--artifacts',
        str(releases / 'runners'), '--runtime-lock', str(lock), '--output', str(output),
        '--python-base-image', PYTHON_BASE, '--runner-base-image', RUNNER_BASE],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Traceback' not in result.stderr and 'Context preparation failed:' in result.stderr
    assert not output.exists()
