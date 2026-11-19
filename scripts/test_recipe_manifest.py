"""The recipe manifest lists every publishable Dockerfile recipe and warns, never refuses."""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('check_recipe_manifest', Path(__file__).with_name('check-recipe-manifest.py'))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
ROOT = Path(__file__).resolve().parents[1]


def test_the_repository_manifest_is_complete_and_consistent():
    assert module.check(ROOT) == []


def test_drift_is_a_warning_with_exit_zero(tmp_path, capsys, monkeypatch):
    root = tmp_path / 'repo'
    (root / 'recipes').mkdir(parents=True)
    shutil.copy(ROOT / 'CHANGELOG.md', root / 'CHANGELOG.md')
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    manifest['recipes'] = [{'name': 'ghost', 'path': 'recipes/ghost', 'version': 'one'}]
    (root / 'recipes' / 'manifest.json').write_text(json.dumps(manifest))
    (root / 'recipes' / 'unlisted').mkdir()
    (root / 'recipes' / 'unlisted' / 'Dockerfile').write_text('FROM scratch\n')
    warnings = module.check(root)
    assert any('ghost' in warning and 'not a directory' in warning for warning in warnings)
    assert any('recipes/unlisted' in warning and 'not in the manifest' in warning for warning in warnings)
    assert any('version' in warning for warning in warnings)
    monkeypatch.setattr(sys, 'argv', ['check-recipe-manifest.py', '--root', str(root)])
    assert module.main() == 0
    assert 'WARNING:' in capsys.readouterr().out
