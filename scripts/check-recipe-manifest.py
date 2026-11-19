#!/usr/bin/env python3
"""Check recipes/manifest.json: the publishable recipe directories and their versions.

Every finding is a WARNING and the exit status is 0, except a manifest that cannot
be read at all (2): nothing here refuses a release over metadata.
Usage: check-recipe-manifest.py [--root <repository>]
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = 'uxmaltech-collab.recipe-manifest/v1'
SEMVER = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')
SLUG = re.compile(r'[a-z0-9][a-z0-9-]{0,50}')
# Directories of Dockerfile recipes that are copies or helpers, not publishable here.
NOT_PUBLISHED = ('recipes/templates/',)


def check(root: Path) -> list[str]:
    path = root / 'recipes' / 'manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    warnings = []
    if manifest.get('schema') != SCHEMA:
        warnings.append(f'schema is {manifest.get("schema")!r}, expected {SCHEMA!r}')
    version = manifest.get('repository_version', '')
    if not SEMVER.fullmatch(version):
        warnings.append(f'repository_version {version!r} is not X.Y.Z')
    changelog = root / 'CHANGELOG.md'
    if not changelog.is_file():
        warnings.append('CHANGELOG.md is missing')
    elif re.search(rf'^## \[?{re.escape(version)}\]?(\s|$)', changelog.read_text(encoding='utf-8'), re.M) is None:
        warnings.append(f'CHANGELOG.md has no section for {version}')
    seen, listed = set(), set()
    for entry in manifest.get('recipes', []):
        name, where = entry.get('name', ''), entry.get('path', '')
        label = name or where or '?'
        if not SLUG.fullmatch(name):
            warnings.append(f'{label}: name must match {SLUG.pattern}')
        if name in seen:
            warnings.append(f'{label}: duplicate name')
        seen.add(name)
        if not SEMVER.fullmatch(entry.get('version', '')):
            warnings.append(f'{label}: version {entry.get("version")!r} is not X.Y.Z')
        directory = root / where
        if not directory.is_dir():
            warnings.append(f'{label}: path {where!r} is not a directory')
            continue
        listed.add(where)
        if not (directory / entry.get('dockerfile', 'Dockerfile')).is_file():
            warnings.append(f'{label}: no {entry.get("dockerfile", "Dockerfile")} in {where}')
        if entry.get('smoke') and not (directory / entry['smoke']).is_file():
            warnings.append(f'{label}: smoke {entry["smoke"]!r} is not a file in {where}')
    for dockerfile in sorted((root / 'recipes').rglob('Dockerfile')):
        directory = dockerfile.parent.relative_to(root).as_posix()
        if directory not in listed and not directory.startswith(NOT_PUBLISHED):
            warnings.append(f'{directory}: has a Dockerfile and is not in the manifest')
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        warnings = check(args.root)
    except (OSError, ValueError) as error:
        print(f'cannot read recipes/manifest.json: {error}', file=sys.stderr)
        return 2
    for warning in warnings:
        print('WARNING: ' + warning)
    listed = len(json.loads((args.root / 'recipes' / 'manifest.json').read_text(encoding='utf-8'))['recipes'])
    print(f'recipe manifest: {listed} recipe(s), {len(warnings)} warning(s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
