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


def test_the_recipe_lock_records_the_current_bytes_of_every_file_it_lists():
    """compatibility/collab-image-recipes.lock.json is the digest list a builder verifies; regenerate it with each recipe change."""
    import hashlib
    lock = json.loads((ROOT / 'compatibility' / 'collab-image-recipes.lock.json').read_text())
    stale = [name for name, digest in lock['files'].items()
             if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    assert stale == []


def test_the_repository_manifest_uses_the_neutral_schema_id():
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    assert manifest['schema'] == 'collab.recipes-manifest/v1'


def test_every_copied_source_of_a_listed_recipe_resolves_inside_its_release_tree():
    """With the ARG defaults applied: a source is in the recipe's path or its shared paths, or the builder supplies it."""
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    resolved = 0
    for entry in manifest['recipes']:
        text = (ROOT / entry['path'] / entry['dockerfile']).read_text()
        warnings = []
        module.check_copy_sources(ROOT, entry['path'], entry.get('shared'), set(entry.get('context_inputs', [])),
                                  entry['name'], text, warnings)
        assert warnings == [], warnings
        sources = module.copy_sources(text)
        assert all(unresolved is None for _, unresolved in sources), (entry['name'], sources)
        resolved += len(sources)
    assert resolved > 20


def test_the_runner_base_entrypoint_resolves_through_its_context_argument_default():
    """The review's scenario: the default of RUNNER_BASE_CONTEXT named a directory the release tree does not hold."""
    entry = next(e for e in json.loads((ROOT / 'recipes' / 'manifest.json').read_text())['recipes']
                 if e['name'] == 'collab-runners-runner-base')
    text = (ROOT / entry['path'] / 'Dockerfile').read_text()
    assert module.copy_sources(text) == [('recipes/collab-runners/runner-base/entrypoint-jit.sh', None)]
    assert (ROOT / 'recipes/collab-runners/runner-base/entrypoint-jit.sh').is_file()
    assert not (ROOT / 'containers').exists()


def test_a_copy_source_the_release_tree_does_not_hold_warns(tmp_path):
    root = repository(tmp_path, None)
    entry = recipe(root, 'base', 'ARG CTX=containers/base\nFROM scratch\nCOPY ${CTX}/entry.sh /entry.sh\nCOPY collab-release /c\nCOPY --from=x /a /b\n')
    repository(tmp_path, good_manifest(entry))
    warnings = module.check(root)
    assert any("COPY source 'containers/base/entry.sh' does not exist in the release tree" in w for w in warnings)
    assert any("COPY source 'collab-release' does not exist" in w for w in warnings)
    assert len(warnings) == 2
    entry['context_inputs'] = ['collab-release']
    repository(tmp_path, good_manifest(entry))
    assert [w for w in module.check(root) if 'collab-release' in w] == [
        "base: context_inputs names 'collab-release' and no context entry says what fills it; "
        'the console cannot resolve it and the build is not made']
    entry['context'] = [{'name': 'collab-release', 'kind': 'artifact', 'component': 'example-org/example-cli', 'version': '>=0.1.0'}]
    repository(tmp_path, good_manifest(entry))
    assert [w for w in module.check(root) if 'collab-release' in w] == []


def test_a_copy_source_outside_the_recipe_and_its_shared_paths_warns(tmp_path):
    root = repository(tmp_path, None)
    (root / 'common').mkdir()
    (root / 'common' / 'tool.py').write_text('')
    (root / 'other').mkdir()
    (root / 'other' / 'file').write_text('')
    entry = recipe(root, 'one', 'FROM scratch\nCOPY common/tool.py /t\nCOPY other/file /o\n')
    repository(tmp_path, good_manifest(entry))
    warnings = module.check(root)
    assert any("COPY source 'common/tool.py' is outside the recipe path and its shared paths" in w for w in warnings)
    assert any("COPY source 'other/file' is outside" in w for w in warnings)
    entry['shared'] = ['common']
    repository(tmp_path, good_manifest(entry))
    warnings = module.check(root)
    assert not any('common/tool.py' in w for w in warnings) and any('other/file' in w for w in warnings)


def test_a_copy_source_that_depends_on_an_argument_without_default_warns_and_the_rest_is_checked(tmp_path):
    root = repository(tmp_path, None)
    entry = recipe(root, 'one', 'FROM scratch\nARG CTX\nCOPY ${CTX}/f /f\nCOPY recipes/one/Dockerfile /d\n')
    repository(tmp_path, good_manifest(entry))
    warnings = module.check(root)
    assert warnings == ["one: COPY source '${CTX}/f' depends on build argument CTX, which has no default; it was not checked"]


def test_a_wrong_typed_context_inputs_warns(tmp_path):
    root = repository(tmp_path, None)
    entry = recipe(root, 'one')
    entry['context_inputs'] = 'collab-release'
    repository(tmp_path, good_manifest(entry))
    assert module.check(root) == ['one: context_inputs must be a list of relative names']


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


def test_every_base_a_recipe_starts_from_is_declared_as_its_parent():
    """No recipe of the manifest takes its base through an undeclared `ARG ... FROM ${...}`: each such argument is the
    `build_arg` of its `parent` (a recipe of this manifest, or a pin for the operating-system image of runner-base)."""
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    by_name = {entry['name']: entry for entry in manifest['recipes']}
    for entry in manifest['recipes']:
        text = (ROOT / entry['path'] / entry['dockerfile']).read_text()
        bases = module.undeclared_bases(text)
        assert bases == [entry['parent']['build_arg']], (entry['name'], bases, entry.get('parent'))
        parent = entry['parent']
        if 'recipe' in parent:
            assert parent['version'] == by_name[parent['recipe']]['version']
    assert by_name['collab-runners-runner-base']['parent'] == {'pin': 'runner-base-os', 'build_arg': 'RUNNER_BASE_OS_IMAGE'}
    assert by_name['android']['parent']['recipe'] == 'collab-runners-runner-agent-base'
    # The pin is a neutral profile name: no registry, tag or digest of any organization is in the manifest.
    assert not any('@sha256:' in json.dumps(entry.get('parent')) or '/' in json.dumps(entry.get('parent', {}).get('pin', ''))
                   for entry in manifest['recipes'])


def test_every_context_input_says_what_fills_it_with_the_runtime_of_the_lock_and_no_pinned_version():
    manifest = json.loads((ROOT / 'recipes' / 'manifest.json').read_text())
    runtime = json.loads((ROOT / 'compatibility' / 'collab-runtime.lock.json').read_text())['runtime']
    needing = [entry for entry in manifest['recipes'] if entry.get('context_inputs')]
    assert len(needing) == 9
    for entry in needing:
        assert entry['context'] == [{'name': 'collab-release', 'kind': 'artifact', 'component': runtime['repository'],
                                     'version': '>=' + runtime['version']}], entry['name']
    assert not any(entry.get('context') for entry in manifest['recipes'] if not entry.get('context_inputs'))


def test_the_three_parent_forms_are_read_and_a_malformed_one_warns(tmp_path):
    root = repository(tmp_path, None)
    os_based = recipe(root, 'os-based', 'ARG OS_IMAGE\nFROM ${OS_IMAGE}\n')
    os_based['parent'] = {'pin': 'example-os', 'build_arg': 'OS_IMAGE'}
    foreign = recipe(root, 'foreign', 'ARG AGENT_IMAGE\nFROM ${AGENT_IMAGE} AS agents\n')
    foreign['parent'] = {'component': 'containers/example-agent-base', 'version': '^0.4.0', 'build_arg': 'AGENT_IMAGE'}
    entry = recipe(root, 'entry', 'ARG AGENT_IMAGE\nFROM ${AGENT_IMAGE}\n')
    entry['parent'] = {'component': 'example-org/example-images', 'recipe': 'example-base', 'version': '0.2.0', 'build_arg': 'AGENT_IMAGE'}
    repository(tmp_path, good_manifest(os_based, foreign, entry))
    assert module.check(root) == []
    os_based['parent'] = {'pin': 'Example/OS:latest', 'build_arg': 'OS_IMAGE'}
    foreign['parent'] = {'component': 'containers/example-agent-base', 'build_arg': 'AGENT_IMAGE'}
    entry['parent'] = {'pin': 'example-os', 'version': '1', 'build_arg': 'OTHER'}
    repository(tmp_path, good_manifest(os_based, foreign, entry))
    warnings = module.check(root)
    assert any(w.startswith('os-based: parent pin must be a profile name') for w in warnings)
    assert 'foreign: parent component must name a string component and version, and a string recipe if any' in warnings
    assert "entry: parent pin 'example-os' names nothing else; version is ignored" in warnings
    assert 'entry: the Dockerfile does not declare ARG OTHER' in warnings
    assert any(w.startswith('entry: a FROM starts from ${AGENT_IMAGE}, which has no default') for w in warnings)


def test_a_base_taken_through_an_argument_without_default_and_without_parent_warns(tmp_path):
    root = repository(tmp_path, None)
    plain = recipe(root, 'plain', 'ARG BASE\nFROM ${BASE}\nARG PINNED=docker.io/library/debian@sha256:' + 'a' * 64 + '\nFROM ${PINNED}\n')
    repository(tmp_path, good_manifest(plain))
    assert module.check(root) == [
        "plain: a FROM starts from ${BASE}, which has no default and is not the parent's build_arg; declare the base as parent"]


def test_a_malformed_context_warns_and_the_rest_is_checked(tmp_path):
    root = repository(tmp_path, None)
    entry = recipe(root, 'one', 'FROM scratch\nCOPY collab-release /c\n')
    entry['context_inputs'] = ['collab-release']
    entry['context'] = [{'name': '../up', 'kind': 'artifact', 'component': 'x', 'version': '*'},
                        {'name': 'collab-release', 'kind': 'image', 'component': 'x', 'version': '*'}]
    repository(tmp_path, good_manifest(entry))
    warnings = module.check(root)
    assert sum('a context entry must be an object' in w for w in warnings) == 2
    assert any("context_inputs names 'collab-release' and no context entry" in w for w in warnings)
    entry['context'] = 'collab-release'
    repository(tmp_path, good_manifest(entry))
    assert 'one: context must be a list of {name, kind, component, version} entries' in module.check(root)


# --- versions against the previous release -------------------------------------------------------

def git_run(root, *arguments):
    import subprocess
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Example', '-c', 'user.email=example@example.test',
                    '-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false', *arguments], check=True, capture_output=True)


def released(tmp_path):
    """A repository tagged v0.1.0 with a recipe that copies one shared file, a recipe with a parent and a bystander."""
    root = tmp_path / 'repo'
    (root / 'recipes').mkdir(parents=True)
    (root / 'common').mkdir()
    (root / 'common' / 'tool.py').write_text('v1')
    (root / 'common' / 'test_tool.py').write_text('t1')
    (root / 'CHANGELOG.md').write_text(CHANGELOG)
    base = recipe(root, 'base', 'FROM scratch\n')
    child = recipe(root, 'child', 'ARG BASE\nFROM ${BASE}\nCOPY common/tool.py /t\nCOPY collab-release /c\n')
    child.update(shared=['common'], parent={'recipe': 'base', 'version': '0.1.0', 'build_arg': 'BASE'},
                 context_inputs=['collab-release'],
                 context=[{'name': 'collab-release', 'kind': 'artifact', 'component': 'example-org/example-cli', 'version': '*'}])
    other = recipe(root, 'other', 'FROM scratch\nCOPY common/tool.py /t\n')
    other.update(shared=['common'])
    (root / 'recipes' / 'manifest.json').write_text(json.dumps(good_manifest(base, child, other)))
    git_run(root, 'init', '-q', '-b', 'main')
    git_run(root, 'add', '-A')
    git_run(root, 'commit', '-q', '-m', 'release')
    git_run(root, 'tag', 'v0.1.0')
    return root


def bump(root, name, version='0.1.1'):
    path = root / 'recipes' / 'manifest.json'
    manifest = json.loads(path.read_text())
    for entry in manifest['recipes']:
        if entry['name'] == name:
            entry['version'] = version
        if entry.get('parent', {}).get('recipe') == name:
            entry['parent']['version'] = version
    path.write_text(json.dumps(manifest))


def test_an_unchanged_tree_has_no_version_warning(tmp_path):
    assert module.check_changes(released(tmp_path)) == []


def test_a_change_to_a_shared_file_a_recipe_copies_asks_for_its_version_and_leaves_the_others(tmp_path):
    root = released(tmp_path)
    (root / 'common' / 'tool.py').write_text('v2')
    warnings = module.check_changes(root)
    assert sorted(w.split(':')[0] for w in warnings) == ['child', 'other']
    assert all('common/tool.py changed since v0.1.0 but its version is still 0.1.0' in w for w in warnings)
    bump(root, 'child')
    bump(root, 'other')
    assert module.check_changes(root) == []


def test_a_shared_file_no_dockerfile_copies_does_not_ask_for_a_version(tmp_path):
    root = released(tmp_path)
    (root / 'common' / 'test_tool.py').write_text('t2')
    (root / 'common' / 'new-untracked.txt').write_text('x')
    assert module.check_changes(root) == []


def test_a_change_to_the_recipes_own_dockerfile_or_files_asks_for_its_version(tmp_path):
    root = released(tmp_path)
    (root / 'recipes' / 'base' / 'Dockerfile').write_text('FROM scratch\nLABEL a=b\n')
    warnings = module.check_changes(root)
    assert len(warnings) == 1 and warnings[0].startswith('base: recipes/base/Dockerfile changed')


def test_a_moved_parent_asks_for_the_childs_version(tmp_path):
    root = released(tmp_path)
    bump(root, 'base')
    warnings = module.check_changes(root)
    assert any(w.startswith('child: the parent base moved from 0.1.0 to 0.1.1') for w in warnings)
    assert not any(w.startswith('base:') for w in warnings)


def test_the_comparison_uses_the_named_reference_and_skips_without_one(tmp_path):
    root = released(tmp_path)
    (root / 'common' / 'tool.py').write_text('v2')
    git_run(root, 'commit', '-q', '-am', 'change')
    git_run(root, 'tag', 'v0.1.1')
    assert module.check_changes(root) == []  # the latest tag already holds the change
    assert len(module.check_changes(root, since='v0.1.0')) == 2
    plain = tmp_path / 'plain'
    plain.mkdir()
    assert module.check_changes(plain) == []  # not a git checkout: skipped, never refused
    assert module.check_changes(root, since='no-such-ref')[0].startswith('the recipe versions were not compared with no-such-ref')


def test_the_command_reports_the_version_warnings_and_exits_zero(tmp_path, capsys):
    root = released(tmp_path)
    (root / 'common' / 'tool.py').write_text('v2')
    status, out = run(root, capsys)
    assert status == 0 and 'WARNING: child: common/tool.py changed since v0.1.0' in out
    status, out = run(root, capsys, '--since', 'v0.1.0')
    assert status == 0 and '2 warning(s)' in out
    status, out = run(root, capsys, '--since')
    assert status == 0 and '--since needs a value' in out
