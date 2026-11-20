"""The recipe manifest lists every publishable Dockerfile recipe and warns, never refuses."""
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('check_recipe_manifest', Path(__file__).with_name('check-recipe-manifest.py'))
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = '# Changelog\n\n## 0.1.0\n\nfirst\n'


def repository(tmp_path, manifest, changelog=CHANGELOG):
    """A throwaway repository holding the given manifest document (a dict or raw text)."""
    root = tmp_path / 'repo'
    (root / 'recipes').mkdir(parents=True, exist_ok=True)
    if changelog is not None:
        (root / 'CHANGELOG.md').write_text(changelog)
    if manifest is not None:
        text = manifest if isinstance(manifest, str) else json.dumps(manifest)
        (root / 'recipes' / 'manifest.json').write_text(text)
    return root


def recipe(root, name, dockerfile='FROM scratch\n'):
    directory = root / 'recipes' / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'Dockerfile').write_text(dockerfile)
    return {'name': name, 'path': f'recipes/{name}', 'version': '0.1.0'}


def run(root, capsys, *arguments):
    """The exit status and the output of the command for a repository root."""
    status = module.main(['--root', str(root), *arguments])
    return status, capsys.readouterr().out


def good_manifest(*entries):
    return {'schema': module.SCHEMA, 'repository_version': '0.1.0', 'recipes': list(entries)}


def test_the_repository_manifest_is_complete_and_consistent():
    assert module.check(ROOT) == []


def test_the_repository_manifest_uses_the_neutral_schema_id():
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    assert manifest['schema'] == 'collab.recipes-manifest/v1'


def test_every_copied_source_of_a_listed_recipe_exists_in_the_tree():
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    missing = []
    for entry in manifest['recipes']:
        text = (ROOT / entry['path'] / entry['dockerfile']).read_text().replace('\\\n', ' ')
        for line in text.splitlines():
            tokens = line.split()
            if not tokens or tokens[0] != 'COPY' or any(token.startswith('--from=') for token in tokens):
                continue
            sources = [token for token in tokens[1:-1] if not token.startswith('--')]
            # `collab-release` is a build-context artifact the builder places at the context root, and a
            # source that names a build argument is resolved by the build, not by the tree.
            missing += [f'{entry["name"]}: {source}' for source in sources
                        if source != 'collab-release' and '$' not in source and not (ROOT / source).exists()]
    assert missing == []


def test_a_recipe_takes_its_bindings_from_plan_time_inputs_not_from_literals():
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    by_name = {entry['name']: entry for entry in manifest['recipes']}
    resolver = by_name['collab-runners-runner-resolver-android']
    assert {'RUNNER_JOURNEY_REPOSITORY', 'RUNNER_JOURNEY_PROFILE', 'RUNNER_JOURNEY_VALIDATOR'} <= set(resolver['inputs'])
    # The Android toolchain is released once, as `android`, and the resolver names that release.
    assert resolver['parent'] == {'recipe': 'android', 'version': by_name['android']['version'],
                                  'build_arg': 'RUNNER_ANDROID_IMAGE'}
    assert not (ROOT / resolver['path'] / 'toolchain-lock.json').exists()
    assert not (ROOT / resolver['path'] / 'scripts').exists()


def test_drift_is_a_warning_with_exit_zero(tmp_path, capsys):
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
    status, out = run(root, capsys)
    assert status == 0
    assert 'WARNING:' in out and '1 recipe(s)' in out


def test_a_missing_manifest_warns_and_the_run_succeeds(tmp_path, capsys):
    root = repository(tmp_path, None)
    status, out = run(root, capsys)
    assert status == 0
    assert 'WARNING: recipes/manifest.json cannot be read' in out
    assert '0 recipe(s), 1 warning(s)' in out


@pytest.mark.parametrize('raw, expected', [
    ('{not json', 'is not valid JSON'),
    ('[]', 'is not a JSON object'),
    ('"text"', 'is not a JSON object'),
])
def test_a_malformed_manifest_warns_and_the_run_succeeds(tmp_path, capsys, raw, expected):
    status, out = run(repository(tmp_path, raw), capsys)
    assert status == 0
    assert expected in out and 'Traceback' not in out


def test_an_unreadable_manifest_warns_and_the_run_succeeds(tmp_path, capsys):
    root = repository(tmp_path, None)
    (root / 'recipes' / 'manifest.json').mkdir()
    status, out = run(root, capsys)
    assert status == 0
    assert 'WARNING: recipes/manifest.json cannot be read' in out


def test_an_unreadable_changelog_is_a_changelog_warning_and_the_other_checks_continue(tmp_path, capsys):
    root = repository(tmp_path, None, changelog=None)
    (root / 'CHANGELOG.md').mkdir()
    repository(tmp_path, {'schema': 'other', 'repository_version': '0.1.0', 'recipes': [recipe(root, 'one')]}, changelog=None)
    status, out = run(root, capsys)
    assert status == 0
    assert 'WARNING: CHANGELOG.md cannot be read' in out
    assert 'manifest.json cannot be read' not in out
    assert "schema is 'other'" in out  # the schema check still ran
    assert '1 recipe(s)' in out


def test_absent_recipes_warn_and_the_counts_come_from_the_one_read(tmp_path, capsys):
    root = repository(tmp_path, {'schema': module.SCHEMA, 'repository_version': '0.1.0'})
    status, out = run(root, capsys)
    assert status == 0
    assert 'WARNING: recipes is absent' in out
    assert '0 recipe(s), 1 warning(s)' in out


def test_the_manifest_is_read_once(tmp_path, capsys, monkeypatch):
    root = repository(tmp_path, good_manifest())
    reads = []
    original = Path.read_text

    def counting(self, *args, **kwargs):
        reads.append(self.name)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', counting)
    status, _ = run(root, capsys)
    assert status == 0
    assert reads.count('manifest.json') == 1


def test_a_changing_manifest_cannot_crash_the_count(tmp_path, capsys, monkeypatch):
    """The count is taken from the validated read, so a file that changes afterwards is not read again."""
    root = repository(tmp_path, None)
    repository(tmp_path, good_manifest(recipe(root, 'one')))
    original = module.read_manifest

    def read_then_break(path):
        result = original(path)
        (path / 'recipes' / 'manifest.json').write_text('{broken')
        return result

    monkeypatch.setattr(module, 'read_manifest', read_then_break)
    status, out = run(root, capsys)
    assert status == 0
    assert '1 recipe(s)' in out


def test_a_non_list_recipes_value_warns(tmp_path, capsys):
    status, out = run(repository(tmp_path, {'schema': module.SCHEMA, 'repository_version': '0.1.0', 'recipes': {'a': 1}}), capsys)
    assert status == 0
    assert 'WARNING: recipes is not a list' in out and '0 recipe(s)' in out


def test_wrong_typed_entries_and_fields_warn_and_the_valid_entry_is_still_checked(tmp_path, capsys):
    root = repository(tmp_path, None)
    good = recipe(root, 'good')
    good_broken = {'name': 'broken-file', 'path': 'recipes/broken-file', 'version': '0.1.0'}
    (root / 'recipes' / 'broken-file').mkdir()
    entries = [
        'not an object',
        42,
        {'name': 5, 'path': ['x'], 'version': 3, 'dockerfile': 7},
        {'name': 'escape', 'path': '../outside', 'version': '0.1.0'},
        {'name': 'absolute', 'path': '/etc', 'version': '0.1.0'},
        {'name': 'typed', 'path': 'recipes/good', 'version': '0.1.0', 'smoke': 5, 'shared': 'x', 'parent': [], 'inputs': [], 'helpers': {}},
        good_broken,
        good,
    ]
    repository(tmp_path, good_manifest(*entries))
    status, out = run(root, capsys)
    assert status == 0 and 'Traceback' not in out
    for expected in ('recipes[0] is not an object', 'recipes[1] is not an object', 'name must be a string',
                     'must be a relative path inside the repository', 'smoke 5 must be null',
                     'shared must be a list', 'parent must be an object', 'inputs must map', 'helpers must be a list',
                     'no Dockerfile in broken-file'):
        assert expected in out, expected
    # The valid entry raised nothing: only warnings about the broken ones are present.
    assert 'good:' not in out


def test_a_missing_root_value_warns_and_uses_the_default_root(capsys):
    assert module.main(['--root']) == 0
    out = capsys.readouterr().out
    assert 'WARNING: --root needs a value; the default repository root is used' in out
    assert f'{len(json.loads((ROOT / "recipes/manifest.json").read_text())["recipes"])} recipe(s)' in out


def test_an_empty_root_option_and_an_unknown_option_warn(capsys):
    assert module.main(['--root=', '--bogus']) == 0
    out = capsys.readouterr().out
    assert '--root needs a value' in out and 'ignored the unknown option' in out


def test_the_former_schema_spelling_is_read_with_one_warning(tmp_path, capsys):
    root = repository(tmp_path, None)
    entry = recipe(root, 'one')
    manifest = good_manifest(entry)
    manifest['schema'] = 'uxmaltech-collab.recipes-manifest/v1'
    repository(tmp_path, manifest)
    warnings = module.check(root)
    assert [w for w in warnings if 'schema' in w] == [
        "schema 'uxmaltech-collab.recipes-manifest/v1' is the former spelling of 'collab.recipes-manifest/v1'; it was read as that schema"]
    assert len(warnings) == 1
    status, out = run(root, capsys)
    assert status == 0 and '1 recipe(s), 1 warning(s)' in out


def test_parent_inputs_and_helpers_must_match_the_recipes(tmp_path):
    root = repository(tmp_path, None)
    base = recipe(root, 'base', 'FROM scratch\nCOPY x /usr/local/bin/tool\n')
    base['helpers'] = [{'capability': 'tool', 'path': '/usr/local/bin/tool'},
                       {'capability': 'ghost', 'path': '/usr/local/bin/ghost'}]
    derived = recipe(root, 'derived', 'ARG BASE\nFROM ${BASE}\nARG KNOWN=\n')
    derived['parent'] = {'recipe': 'base', 'version': '9.9.9', 'build_arg': 'BASE'}
    derived['inputs'] = {'KNOWN': 'a.fact', 'MISSING': 'b.fact'}
    orphan = recipe(root, 'orphan')
    orphan['parent'] = {'recipe': 'nowhere', 'version': '0.1.0', 'build_arg': 'BASE'}
    orphan['shared'] = ['recipes/not-there']
    repository(tmp_path, good_manifest(base, derived, orphan))
    warnings = module.check(root)
    assert 'base: the Dockerfile does not install /usr/local/bin/ghost' in warnings
    assert 'derived: parent base is pinned at 9.9.9 but the manifest lists 0.1.0' in warnings
    assert 'derived: the Dockerfile does not declare ARG MISSING' in warnings
    assert "orphan: parent recipe 'nowhere' is not in the manifest" in warnings
    assert "orphan: shared path 'recipes/not-there' does not exist" in warnings
    assert not any('KNOWN' in warning or '/usr/local/bin/tool' in warning for warning in warnings)
