#!/usr/bin/env python3
"""Check recipes/manifest.json: the publishable recipe directories and their versions.

Every finding is a WARNING and the exit status is always 0: nothing here refuses a
release over metadata. A manifest or changelog that is missing, unreadable or malformed,
a field of the wrong type and an option without its value each warn; the checks that do
not depend on the affected part still run. The manifest is read once.
Besides the manifest itself it compares each recipe with the previous release: a recipe whose
Dockerfile, copied source (the recipe's own files and the shared paths it copies) or parent version
changed since the previous release tag, and whose version did not, warns. `--since <ref>` names
another reference; with no earlier release tag the comparison is skipped.
Usage: check-recipe-manifest.py [--root <repository>] [--since <ref>]
"""
import json
import re
import subprocess
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
    context_inputs = check_context_inputs(entry.get('context_inputs'), label, warnings)
    if text is not None:
        check_copy_sources(root, where, entry.get('shared'), context_inputs, label, text, warnings)
    check_context(entry.get('context'), context_inputs, label, warnings)
    check_parent(entry.get('parent'), label, text, versions, warnings)
    check_inputs(entry.get('inputs'), label, text, warnings)
    if text is not None:
        parent = entry.get('parent')
        carried = parent.get('build_arg') if isinstance(parent, dict) else None
        mapped = set(entry['inputs']) if isinstance(entry.get('inputs'), dict) else set()
        for name in required_arguments(text):
            if name != carried and name not in mapped:
                warnings.append(f'{label}: the Dockerfile stops without build argument {name}, which has no default, '
                                'is not the parent\'s build_arg and is not mapped under inputs; map it to the fact that '
                                'carries it (or give it a default when it is a constant of the recipe)')
        for name in undeclared_bases(text):
            if name != carried:
                warnings.append(f'{label}: a FROM starts from ${{{name}}}, which has no default and is not the parent\'s '
                                'build_arg; declare the base as parent')
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


def check_context_inputs(value, label, warnings):
    """Names the builder places at the root of the build context itself (not part of the tree)."""
    if value is None:
        return set()
    if not isinstance(value, list) or not all(inside(Path('.'), item) for item in value):
        warnings.append(f'{label}: context_inputs must be a list of relative names')
        return set()
    return {Path(item).parts[0] for item in value}


def copy_sources(text):
    """The (source, unresolved build argument or None) pairs of every COPY that reads the build context."""
    text = re.sub(r'\\\n', ' ', text)
    defaults = dict(re.findall(r'^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)=(\S*)', text, re.M))
    found = []
    for line in text.splitlines():
        tokens = line.split()
        if not tokens or tokens[0].upper() != 'COPY' or any(token.startswith('--from=') for token in tokens):
            continue
        for source in [token for token in tokens[1:-1] if not token.startswith('--')]:
            unresolved = None
            for _ in range(5):
                names = re.findall(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)', source)
                if not names:
                    break
                name = next(a or b for a, b in names)
                if name not in defaults:
                    unresolved = name
                    break
                source = re.sub(rf'\$\{{{name}\}}|\${name}\b', defaults[name].replace('\\', '\\\\'), source)
            found.append((source, unresolved))
    return found


def check_copy_sources(root, where, shared, context_inputs, label, text, warnings):
    """Every COPY source resolves, with the ARG defaults applied, inside the tree this recipe is released with."""
    allowed = [Path(where).as_posix()] + [Path(item).as_posix() for item in shared if inside(root, item)] \
        if isinstance(shared, list) else [Path(where).as_posix()]
    for source, unresolved in copy_sources(text):
        if unresolved is not None:
            warnings.append(f'{label}: COPY source {source!r} depends on build argument {unresolved}, which has no default; '
                            'it was not checked')
        elif Path(source).parts[:1] and Path(source).parts[0] in context_inputs:
            continue
        elif not inside(root, source):
            warnings.append(f'{label}: COPY source {source!r} is not a relative path inside the build context')
        elif not any(root.glob(Path(source).as_posix())):
            warnings.append(f'{label}: COPY source {source!r} does not exist in the release tree; '
                            'declare it under context_inputs if the builder supplies it')
        elif not any(Path(source).as_posix() == place or Path(source).as_posix().startswith(place + '/') for place in allowed):
            warnings.append(f'{label}: COPY source {source!r} is outside the recipe path and its shared paths; '
                            'add its directory to shared')


CONTEXT_KINDS = ('tree', 'artifact')
PROFILE = re.compile(r'[a-z0-9][a-z0-9._-]{0,99}')


def check_context(context, context_inputs, label, warnings):
    """What fills each name of `context_inputs`: entries shaped as a container recipe's `version.json` `build.context`
    (`{name, kind: tree|artifact, component: <release index key>, version: <constraint>}`). The version the organization
    runs is chosen by its console (its adoption); the recipe only states the component and the versions it works with."""
    filled = set()
    if context is not None and not isinstance(context, list):
        warnings.append(f'{label}: context must be a list of {{name, kind, component, version}} entries')
        context = []
    for item in context or []:
        if (not isinstance(item, dict) or not isinstance(item.get('name'), str) or not inside(Path('.'), item['name'])
                or item.get('kind') not in CONTEXT_KINDS or not isinstance(item.get('component'), str) or not item['component']
                or not isinstance(item.get('version'), str) or not item['version'].strip()):
            warnings.append(f'{label}: a context entry must be an object with a relative name, kind tree or artifact, '
                            f'a component and a version constraint, found {show(item)}')
            continue
        filled.add(Path(item['name']).parts[0])
    for name in sorted(context_inputs - filled):
        warnings.append(f'{label}: context_inputs names {name!r} and no context entry says what fills it; '
                        'the console cannot resolve it and the build is not made')


def check_parent(parent, label, text, versions, warnings):
    """A parent is one of: a recipe of this manifest (`recipe`, `version`), the image of a recipe of another released
    component (`component`, optional `recipe`, `version`), or an image no recipe builds, pinned by the organization under a
    neutral profile (`pin`). Each names the `build_arg` that carries it."""
    if parent is None:
        return
    if not isinstance(parent, dict) or not isinstance(parent.get('build_arg'), str):
        warnings.append(f'{label}: parent must be an object with a string build_arg and one of recipe, component or pin')
        return
    if 'pin' in parent:
        if not isinstance(parent['pin'], str) or not PROFILE.fullmatch(parent['pin']):
            warnings.append(f'{label}: parent pin must be a profile name matching {PROFILE.pattern}, found {show(parent["pin"])}')
        elif set(parent) - {'pin', 'build_arg'}:
            warnings.append(f'{label}: parent pin {parent["pin"]!r} names nothing else; '
                            f'{", ".join(sorted(set(parent) - {"pin", "build_arg"}))} is ignored')
    elif 'component' in parent:
        if (not isinstance(parent['component'], str) or not parent['component'] or not isinstance(parent.get('version'), str)
                or ('recipe' in parent and not isinstance(parent['recipe'], str))):
            warnings.append(f'{label}: parent component must name a string component and version, and a string recipe if any')
    elif not isinstance(parent.get('recipe'), str) or not isinstance(parent.get('version'), str):
        warnings.append(f'{label}: parent must be an object with string recipe, version and build_arg')
        return
    else:
        released = versions.get(parent['recipe'])
        if released is None:
            warnings.append(f'{label}: parent recipe {parent["recipe"]!r} is not in the manifest')
        elif released != parent['version']:
            warnings.append(f'{label}: parent {parent["recipe"]} is pinned at {parent["version"]} '
                            f'but the manifest lists {released}')
    if text is not None and not declares(text, parent['build_arg']):
        warnings.append(f'{label}: the Dockerfile does not declare ARG {parent["build_arg"]}')
    if text is not None and not starts_from(text, parent['build_arg']):
        warnings.append(f'{label}: no FROM of the Dockerfile starts from ${{{parent["build_arg"]}}}')


def check_inputs(inputs, label, text, warnings):
    """Each plan-time input is a build argument the Dockerfile declares, bound to a fact key `<group>.<fact>`. A key of a
    reserved group is a fact the console or the builder supplies, never the organization's declaration: only the keys
    of SUPPLIED are filled."""
    if inputs is None:
        return
    if not isinstance(inputs, dict):
        warnings.append(f'{label}: inputs must map a build argument to the fact it carries')
        return
    for arg, fact in inputs.items():
        if not ARG_NAME.fullmatch(arg) or not isinstance(fact, str) or not fact:
            warnings.append(f'{label}: input {show(arg)} must map an ARG_NAME to a fact name')
            continue
        if text is not None and not declares(text, arg):
            warnings.append(f'{label}: the Dockerfile does not declare ARG {arg}')
        if not FACT_KEY.fullmatch(fact):
            warnings.append(f'{label}: input {arg} maps {show(fact)}, which is not a key <group>.<fact> '
                            '(lower case, digits and _); the console cannot read a declaration for it')
        elif fact.partition('.')[0] in RESERVED_GROUPS and fact not in SUPPLIED:
            warnings.append(f'{label}: input {arg} maps {fact}, a key of a reserved group that nobody supplies '
                            f'(supplied: {", ".join(sorted(SUPPLIED))}); it is never passed')


# A fact key is `<group>.<fact>`: the console flattens `recipe_inputs.<recipe>.<group>.<fact>` to it.
FACT_KEY = re.compile(r'[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*')
# Groups an organization never declares: their facts come from the console (the verified release the build is made
# from) or from the builder. A declared key of one of them is left out with a warning by the console and the builder.
RESERVED_GROUPS = frozenset({'release', 'context', 'builder', 'image_pins'})
SUPPLIED = frozenset({
    'release.commit',                  # the console: the commit of the stored release whose tree is built
    'image_pins.digest',               # the builder: the digest of the parent the build record pins
    'builder.resolved_parent_digest',  # the builder: what it observes for the pulled parent (not observed yet)
})
# Arguments BuildKit sets on every build.
AUTOMATIC_ARGS = frozenset({'TARGETARCH', 'TARGETOS', 'TARGETPLATFORM', 'TARGETVARIANT',
                            'BUILDARCH', 'BUILDOS', 'BUILDPLATFORM', 'BUILDVARIANT'})
SHELL_NAME = r'\$\{?([A-Za-z_][A-Za-z0-9_]*)'


def required_arguments(text):
    """The build arguments the Dockerfile cannot build without: declared with no default (by every ARG of that name)
    and then required by a RUN, through `test -n` / `[ -n ... ]` or as the expected digest `sha256sum -c` reads, either
    directly or through a shell variable assigned from it (a `case` arm per architecture, a `for` loop over pins).
    Both arguments of a per-architecture pair are found: each is assigned in its own arm."""
    joined = re.sub(r'\\\n', ' ', text)
    declared = re.findall(r'^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)(=?)', joined, re.M)
    candidates = {name for name, eq in declared if not eq} - {name for name, eq in declared if eq} - AUTOMATIC_ARGS
    aliases, checked = {}, set()
    for line in joined.splitlines():
        if not re.match(r'\s*RUN\b', line):
            continue
        for statement in re.split(r'&&|\|\||;', line):
            names = set(re.findall(SHELL_NAME, statement))
            for variable, source in re.findall(r'(?<![\w$])([A-Za-z_][A-Za-z0-9_]*)="?\$\{([A-Za-z_][A-Za-z0-9_]*)\}"?', statement):
                aliases.setdefault(variable, set()).add(source)
            loop = re.match(r'\s*(?:RUN\s+)?for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+(.*)', statement)
            if loop:
                aliases.setdefault(loop.group(1), set()).update(re.findall(SHELL_NAME, loop.group(2)))
            elif re.search(r'\btest\s+-n\b|\[\s+-n\b', statement) or re.search(r'\bsha256sum\s+(-\S*\s+)*-c\b', statement):
                checked |= names
    pending, seen = list(checked), set()
    while pending:
        name = pending.pop()
        if name not in seen:
            seen.add(name)
            pending.extend(aliases.get(name, ()))
    return sorted(seen & candidates)


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


def starts_from(text, arg):
    return re.search(rf'^\s*FROM\s+(--\S+\s+)*\$\{{?{re.escape(arg)}\}}?(\s|$)', text, re.M) is not None


def undeclared_bases(text):
    """The build arguments a FROM line starts from that have no default: the base must then be declared as `parent`."""
    defaults = dict(re.findall(r'^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)=(\S+)', text, re.M))
    found = re.findall(r'^\s*FROM\s+(?:--\S+\s+)*\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?', text, re.M)
    return sorted({name for name in found if name not in defaults})


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


def git(root, *arguments):
    """The standard output of a git command, or None when it cannot run or fails."""
    try:
        done = subprocess.run(['git', '-C', str(root), *arguments], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def matches(changed, source):
    """True when the changed path is the copied source, below it, or matched by it (a glob)."""
    return (changed == source or changed.startswith(source.rstrip('/') + '/')
            or re.fullmatch(re.escape(source).replace(r'\*', '[^/]*').replace(r'\?', '[^/]'), changed) is not None)


def parent_name(parent):
    """A parent declaration, named for a message: its recipe (or component and recipe) and version, or its pin."""
    if isinstance(parent.get('pin'), str):
        return f"pin {parent['pin']}"
    subject = '/'.join(str(parent[key]) for key in ('component', 'recipe') if isinstance(parent.get(key), str)) or '?'
    return f"recipe {subject} {parent.get('version')}" if parent.get('version') is not None else f'recipe {subject}'


def parent_change(before, after):
    """Why the parent declaration differs: the whole declaration is compared, not only its version."""
    same_base = {key: before.get(key) for key in ('recipe', 'component', 'pin')} == {key: after.get(key) for key in ('recipe', 'component', 'pin')}
    if same_base and before.get('build_arg') == after.get('build_arg') and 'pin' not in after:
        return f"the parent {after.get('recipe')} moved from {before.get('version')} to {after.get('version')}"
    detail = f" (build argument {after.get('build_arg')})" if before.get('build_arg') != after.get('build_arg') else ''
    return f'the parent changed from {parent_name(before)} to {parent_name(after)}{detail}'


def check_changes(root, since=None):
    """Warnings for recipes whose bytes (or parent) changed since the previous release but not their version.

    What a recipe's version covers is what its image is built from: its Dockerfile, every source its Dockerfile
    copies (so a change to a shared path counts only when the file is one the Dockerfile copies) and the version of
    its parent. Nothing here refuses: with no previous release, no readable manifest there or no git, it skips.
    """
    root = Path(root)
    ref = since
    if ref is None:
        described = git(root, 'describe', '--tags', '--abbrev=0', '--match', 'v[0-9]*', 'HEAD')
        ref = described.strip() if described else None
    if not ref:
        return []
    document, _ = read_manifest(root)
    earlier = git(root, 'show', f'{ref}:recipes/manifest.json')
    try:
        before = json.loads(earlier) if earlier else None
    except ValueError:
        before = None
    if document is None or not isinstance(document.get('recipes'), list):
        return []  # the manifest checks already warned
    if not isinstance(before, dict):
        return [f'the recipe versions were not compared with {ref}: it has no readable recipes/manifest.json']
    changed = set((git(root, 'diff', '--name-only', ref, '--') or '').split('\n')) | \
        set((git(root, 'ls-files', '--others', '--exclude-standard') or '').split('\n'))
    changed.discard('')
    old = {e['name']: e for e in (before.get('recipes') or []) if isinstance(e, dict) and isinstance(e.get('name'), str)}
    warnings = []
    for entry in document['recipes']:
        if not isinstance(entry, dict) or not isinstance(entry.get('name'), str) or not isinstance(entry.get('path'), str):
            continue
        previous = old.get(entry['name'])
        if previous is None or previous.get('version') != entry.get('version'):
            continue  # a new recipe, or one whose version already moved
        dockerfile = entry.get('dockerfile') if isinstance(entry.get('dockerfile'), str) else 'Dockerfile'
        recipe_dockerfile = (Path(entry['path']) / dockerfile).as_posix()
        try:
            text = (root / recipe_dockerfile).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        context_inputs = check_context_inputs(entry.get('context_inputs'), entry['name'], [])
        sources = [recipe_dockerfile] + [source for source, unresolved in copy_sources(text)
                                         if unresolved is None and Path(source).parts[:1] and Path(source).parts[0] not in context_inputs]
        causes = sorted({path for path in changed if any(matches(path, source) for source in sources)})
        parent, before_parent = entry.get('parent'), previous.get('parent')
        if parent != before_parent and isinstance(parent, dict) and isinstance(before_parent, dict):
            causes.append(parent_change(before_parent, parent))
        if causes:
            warnings.append(f"{entry['name']}: {', '.join(causes[:3])}{' and more' if len(causes) > 3 else ''} changed since {ref} "
                            f"but its version is still {entry.get('version')}; bump it in recipes/manifest.json")
    return warnings


def options(argv):
    """The repository root, the reference to compare with and the warnings about options that could not be used."""
    root, warnings, index, since = DEFAULT_ROOT, [], 0, None
    while index < len(argv):
        argument = argv[index]
        if argument == '--since':
            if index + 1 < len(argv) and not argv[index + 1].startswith('--'):
                since, index = argv[index + 1], index + 1
            else:
                warnings.append('--since needs a value; the latest release tag is used')
        elif argument.startswith('--since='):
            if argument[len('--since='):]:
                since = argument[len('--since='):]
            else:
                warnings.append('--since needs a value; the latest release tag is used')
        elif argument == '--root':
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
    return root, since, warnings


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if any(argument in ('-h', '--help') for argument in argv):
        print(__doc__)
        return 0
    root, since, warnings = options(argv)
    count = 0
    try:
        found, count = inspect(root)
        warnings += found
        warnings += check_changes(root, since)
    except Exception as error:  # advisory tool: an unexpected failure is a warning, never a refusal
        warnings.append(f'the check stopped early ({type(error).__name__}: {str(error)[:80]})')
    for warning in warnings:
        print('WARNING: ' + warning)
    print(f'recipe manifest: {count} recipe(s), {len(warnings)} warning(s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
