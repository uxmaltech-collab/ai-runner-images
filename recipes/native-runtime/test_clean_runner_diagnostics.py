"""Disposable filesystem checks for the image-only diagnostic removal."""
import importlib.util
from pathlib import Path
import pytest

SPEC = importlib.util.spec_from_file_location('clean_runner', Path(__file__).with_name('clean-runner-diagnostics.py'))
recipe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recipe)


def test_removal_never_reads_logs_or_changes_siblings(tmp_path, monkeypatch):
    diag = tmp_path / '_diag'
    diag.mkdir(mode=0o700)
    (diag / 'log').write_bytes(b'private diagnostic contents')
    binary = tmp_path / 'Runner.Listener'
    binary.write_bytes(b'preserved executable')
    before = binary.stat()
    original = Path.open
    def guarded(path, *args, **kwargs):
        if path.is_relative_to(diag):
            raise AssertionError('Diagnostic contents must never be read')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    recipe.remove_diagnostics(diag, recipe.inventory(diag))
    assert not diag.exists()
    assert binary.read_bytes() == b'preserved executable'
    after = binary.stat()
    assert (after.st_ino, after.st_size, after.st_mode, after.st_mtime_ns) == (
        before.st_ino, before.st_size, before.st_mode, before.st_mtime_ns)


@pytest.mark.parametrize('link_root', [False, True])
def test_symlinks_preserve_external_files(tmp_path, link_root):
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'sentinel'
    sentinel.write_bytes(b'preserve')
    diag = tmp_path / '_diag'
    if link_root:
        diag.symlink_to(outside, target_is_directory=True)
    else:
        diag.mkdir()
        (diag / 'link').symlink_to(sentinel)
    with pytest.raises(ValueError, match='Unexpected diagnostic entry'):
        recipe.inventory(diag)
    assert sentinel.read_bytes() == b'preserve'
    assert diag.exists()


def test_metadata_change_refuses_removal(tmp_path):
    diag = tmp_path / '_diag'
    diag.mkdir()
    before = recipe.inventory(diag)
    (diag / 'later').write_bytes(b'new')
    with pytest.raises(ValueError, match='metadata changed'):
        recipe.remove_diagnostics(diag, before)
    assert (diag / 'later').read_bytes() == b'new'
