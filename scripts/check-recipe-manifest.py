#!/usr/bin/env python3
"""Check recipes/manifest.json: the publishable recipe directories and their versions.

Every finding is a WARNING and the exit status is always 0: nothing here refuses a
release over metadata. A manifest or changelog that is missing, unreadable or malformed,
a field of the wrong type and an option without its value each warn; the checks that do
not depend on the affected part still run. The manifest is read once.
Usage: check-recipe-manifest.py [--root <repository>]
"""
import json
import re
import sys
from pathlib import Path

SCHEMA = 'collab.recipes-manifest/v1'
# The former spelling of the same schema stays readable; it warns once.
FORMER_SCHEMAS = ('uxmaltech-collab.recipes-manifest/v1', 'uxmaltech-collab.recipe-manifest/v1')
SEMVER = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')
SLUG = re.compile(r'[a-z0-9][a-z0-9-]{0,50}')
ARG_NAME = re.compile(r'[A-Z][A-Z0-9_]*')
# Directories of Dockerfile recipes that are copies or helpers, not publishable here.
NOT_PUBLISHED = ('recipes/templates/',)
DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def show(value):
    return repr(value)[:80]


def reason(error):
    return getattr(error, 'strerror', None) or type(error).__name__


def inside(root, relative):
    """True when `relative` is a relative path that stays inside `root`."""
    if not isinstance(relative, str) or not relative or '\x00' in relative:
        return False
    parts = Path(relative)
    return not parts.is_absolute() and '..' not in parts.parts


def read_manifest(root):
    """One read of the manifest: (document or None, warnings)."""
    try:
        text = (root / 'recipes' / 'manifest.json').read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as error:
        return None, [f'recipes/manifest.json cannot be read ({reason(error)}); the manifest checks were skipped']
    try:
        document = json.loads(text)
    except ValueError as error:
        return None, [f'recipes/manifest.json is not valid JSON ({error}); the manifest checks were skipped']
    if not isinstance(document, dict):
        return None, ['recipes/manifest.json is not a JSON object; the manifest checks were skipped']
    return document, []


def dockerfile_text(directory, name, label, warnings):
    try:
        return (directory / name).read_text(encoding='utf-8', errors='replace')
    except OSError:
        warnings.append(f'{label}: no {name} in {directory.name}')
        return None


def check_entry(root, entry, index, versions, seen, listed, warnings):
    """Checks one recipe entry; a wrong-typed field warns and skips only its own check."""
    if not isinstance(entry, dict):
        warnings.append(f'recipes[{index}] is not an object; it was skipped')
        return
    name, where = entry.get('name'), entry.get('path')
    label = name if isinstance(name, str) and name else where if isinstance(where, str) and where else f'recipes[{index}]'
    if not isinstance(name, str) or not SLUG.fullmatch(name):
        warnings.append(f'{label}: name must be a string matching {SLUG.pattern}, found {show(name)}')
    elif name in seen:
        warnings.append(f'{label}: duplicate name')
    else:
        seen.add(name)
    version = entry.get('version')
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        warnings.append(f'{label}: version {show(version)} is not X.Y.Z')
    if not inside(root, where):
        warnings.append(f'{label}: path {show(where)} must be a relative path inside the repository')
        return
    directory = root / where
    if not directory.is_dir():
        warnings.append(f'{label}: path {where!r} is not a directory')
        return
    listed.add(Path(where).as_posix())
    dockerfile = entry.get('dockerfile', 'Dockerfile')
    if not isinstance(dockerfile, str) or not inside(root, dockerfile):
        warnings.append(f'{label}: dockerfile {show(dockerfile)} must be a relative file name')
        dockerfile = 'Dockerfile'
    text = dockerfile_text(directory, dockerfile, label, warnings)
    smoke = entry.get('smoke')
    if smoke is not None:
        if not isinstance(smoke, str) or not inside(root, smoke):
            warnings.append(f'{label}: smoke {show(smoke)} must be null or a relative file name')
        elif not (directory / smoke).is_file():
            warnings.append(f'{label}: smoke {smoke!r} is not a file in {where}')
    check_shared(root, entry.get('shared'), label, warnings)
    check_parent(entry.get('parent'), label, text, versions, warnings)
    check_inputs(entry.get('inputs'), label, text, warnings)
    check_helpers(entry.get('helpers'), label, text, warnings)


def check_shared(root, shared, label, warnings):
    if shared is None:
        return
    if not isinstance(shared, list):
        warnings.append(f'{label}: shared must be a list of paths')
        return
    for item in shared:
        if not inside(root, item):
            warnings.append(f'{label}: shared path {show(item)} must be a relative path inside the repository')
        elif not (root / item).exists():
            warnings.append(f'{label}: shared path {item!r} does not exist')


def check_parent(parent, label, text, versions, warnings):
    """A parent is a recipe of this manifest, referenced by its released version."""
    if parent is None:
        return
    if (not isinstance(parent, dict) or not isinstance(parent.get('recipe'), str)
            or not isinstance(parent.get('version'), str) or not isinstance(parent.get('build_arg'), str)):
        warnings.append(f'{label}: parent must be an object with string recipe, version and build_arg')
        return
    released = versions.get(parent['recipe'])
    if released is None:
        warnings.append(f'{label}: parent recipe {parent["recipe"]!r} is not in the manifest')
    elif released != parent['version']:
        warnings.append(f'{label}: parent {parent["recipe"]} is pinned at {parent["version"]} '
                        f'but the manifest lists {released}')
    if text is not None and not declares(text, parent['build_arg']):
        warnings.append(f'{label}: the Dockerfile does not declare ARG {parent["build_arg"]}')


def check_inputs(inputs, label, text, warnings):
    """Each plan-time input is a build argument the Dockerfile declares, bound to a canon fact."""
    if inputs is None:
        return
    if not isinstance(inputs, dict):
        warnings.append(f'{label}: inputs must map a build argument to the fact it carries')
        return
    for arg, fact in inputs.items():
        if not ARG_NAME.fullmatch(arg) or not isinstance(fact, str) or not fact:
            warnings.append(f'{label}: input {show(arg)} must map an ARG_NAME to a fact name')
        elif text is not None and not declares(text, arg):
            warnings.append(f'{label}: the Dockerfile does not declare ARG {arg}')


def check_helpers(helpers, label, text, warnings):
    """Each stable helper path is installed by the recipe's own Dockerfile."""
    if helpers is None:
        return
    if not isinstance(helpers, list):
        warnings.append(f'{label}: helpers must be a list')
        return
    for helper in helpers:
        if (not isinstance(helper, dict) or not isinstance(helper.get('capability'), str)
                or not isinstance(helper.get('path'), str)):
            warnings.append(f'{label}: a helper must be an object with string capability and path')
        elif text is not None and helper['path'] not in text:
            warnings.append(f'{label}: the Dockerfile does not install {helper["path"]}')


def declares(text, arg):
    return re.search(rf'^\s*ARG\s+{re.escape(arg)}(=|\s|$)', text, re.M) is not None


def inspect(root):
    """The warnings and the recipe count of one validated read of the manifest."""
    manifest, warnings = read_manifest(root)
    if manifest is None:
        return warnings, 0
    schema = manifest.get('schema')
    if schema in FORMER_SCHEMAS:
        warnings.append(f'schema {schema!r} is the former spelling of {SCHEMA!r}; it was read as that schema')
    elif schema != SCHEMA:
        warnings.append(f'schema is {show(schema)}, expected {SCHEMA!r}')
    version = manifest.get('repository_version')
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        warnings.append(f'repository_version {show(version)} is not X.Y.Z')
    else:
        check_changelog(root, version, warnings)
    recipes = manifest.get('recipes')
    if recipes is None:
        warnings.append('recipes is absent; no recipe was checked')
        return warnings, 0
    if not isinstance(recipes, list):
        warnings.append('recipes is not a list; no recipe was checked')
        return warnings, 0
    versions = {entry['name']: entry['version'] for entry in recipes
                if isinstance(entry, dict) and isinstance(entry.get('name'), str) and isinstance(entry.get('version'), str)}
    seen, listed = set(), set()
    for index, entry in enumerate(recipes):
        check_entry(root, entry, index, versions, seen, listed, warnings)
    try:
        dockerfiles = sorted((root / 'recipes').rglob('Dockerfile'))
    except OSError as error:
        warnings.append(f'recipes/ cannot be listed ({reason(error)}); unlisted Dockerfiles were not looked for')
        dockerfiles = []
    for dockerfile in dockerfiles:
        directory = dockerfile.parent.relative_to(root).as_posix()
        if directory not in listed and not directory.startswith(NOT_PUBLISHED):
            warnings.append(f'{directory}: has a Dockerfile and is not in the manifest')
    return warnings, sum(isinstance(entry, dict) for entry in recipes)


def check_changelog(root, version, warnings):
    changelog = root / 'CHANGELOG.md'
    if not changelog.exists():
        warnings.append('CHANGELOG.md is missing')
        return
    try:
        text = changelog.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as error:
        warnings.append(f'CHANGELOG.md cannot be read ({reason(error)}); its section for {version} was not checked')
        return
    if re.search(rf'^## \[?{re.escape(version)}\]?(\s|$)', text, re.M) is None:
        warnings.append(f'CHANGELOG.md has no section for {version}')


def check(root):
    return inspect(Path(root))[0]


def options(argv):
    """The repository root and the warnings about options that could not be used."""
    root, warnings, index = DEFAULT_ROOT, [], 0
    while index < len(argv):
        argument = argv[index]
        if argument == '--root':
            if index + 1 < len(argv) and not argv[index + 1].startswith('--'):
                root, index = Path(argv[index + 1]), index + 1
            else:
                warnings.append('--root needs a value; the default repository root is used')
        elif argument.startswith('--root='):
            if argument[len('--root='):]:
                root = Path(argument[len('--root='):])
            else:
                warnings.append('--root needs a value; the default repository root is used')
        else:
            warnings.append(f'ignored the unknown option {show(argument)}')
        index += 1
    return root, warnings


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if any(argument in ('-h', '--help') for argument in argv):
        print(__doc__)
        return 0
    root, warnings = options(argv)
    count = 0
    try:
        found, count = inspect(root)
        warnings += found
    except Exception as error:  # advisory tool: an unexpected failure is a warning, never a refusal
        warnings.append(f'the check stopped early ({type(error).__name__}: {str(error)[:80]})')
    for warning in warnings:
        print('WARNING: ' + warning)
    print(f'recipe manifest: {count} recipe(s), {len(warnings)} warning(s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
