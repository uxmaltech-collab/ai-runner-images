#!/usr/bin/env python3
"""Prepare an image context using the separately installed, pinned Collab runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import zipfile

from collab.distribution import verify_release
from collab.pack import validate_lock


class ContextPreparationError(ValueError):
    """The declared input or bounded context copy cannot be accepted."""


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _verified_release(artifacts: Path) -> dict:
    try:
        return verify_release(artifacts)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        raise ContextPreparationError('Release artifacts failed verification') from error


def _expected_runtime(path: Path) -> tuple[dict, str]:
    try:
        payload = path.read_bytes()
        lock = json.loads(payload)
        runtime = validate_lock(lock)
    except (ValueError, OSError) as error:
        raise ContextPreparationError('Expected runtime lock is invalid or unavailable') from error
    return runtime, _digest(payload)


def prepare(artifacts: Path, expected_lock: Path, output: Path, python_base: str, runner_base: str) -> dict:
    runtime, lock_digest = _expected_runtime(expected_lock)
    manifest = _verified_release(artifacts)
    if (manifest.get('schema') != 'collab.release/v2'
            or not any(provider['id'] == 'runners' for provider in manifest['providers'])):
        raise ContextPreparationError('Control-plane context requires a verified runners provider release')
    if runtime != manifest['runtime']:
        raise ContextPreparationError('Expected runtime lock differs from the supplied release')
    if any(not isinstance(image, str)
           or not re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', image)
           for image in (python_base, runner_base)):
        raise ContextPreparationError('Python and runner-tool base images require immutable digests')
    if output.exists() or output.is_symlink():
        raise ContextPreparationError('Build context must be a new directory')
    try:
        # Bind copied bytes to the verified closure, including the metadata files
        # not included in manifest.files. No recipe is reread during the copy.
        expected = {entry['name']: entry['sha256'] for entry in manifest['files']}
        for name in ('release-manifest.json', 'SHA256SUMS'):
            expected[name] = _digest((artifacts / name).read_bytes())
        dockerfile = Path(__file__).with_name('Dockerfile')
        if dockerfile.is_symlink() or not dockerfile.is_file():
            raise ContextPreparationError('Recipe Dockerfile must be a regular file')
        recipe_bytes = dockerfile.read_bytes()
        output.mkdir(parents=True, exist_ok=False)
        release = output / 'collab-release'
        release.mkdir()
        for name, expected_digest in expected.items():
            target = release / name
            shutil.copyfile(artifacts / name, target)
            if target.is_symlink() or _digest(target.read_bytes()) != expected_digest:
                raise ContextPreparationError('Copied release artifact differs from its verified identity')
        if _verified_release(release) != manifest:
            raise ContextPreparationError('Copied control-plane release differs from the verified source')
        (output / 'Dockerfile').write_bytes(recipe_bytes)
        receipt = {
            'schema': 'collab.image-context/v1', 'runtime': runtime,
            'release': {'schema': manifest['schema'], 'profile': manifest['profile'],
                        'providers': manifest['providers'],
                        'manifest_sha256': expected['release-manifest.json']},
            'expected_runtime_lock_sha256': lock_digest,
            'recipe': {'dockerfile_sha256': _digest(recipe_bytes)},
            'python_base_image': python_base, 'runner_base_image': runner_base,
            'image_build': 'not-run', 'image_publication': 'not-run', 'host_installation': 'not-run',
            'files': {str(path.relative_to(output)): _digest(path.read_bytes())
                      for path in sorted(output.rglob('*')) if path.is_file()},
        }
        (output / 'context-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    except OSError as error:
        # Retain a newly created partial context for inspection. It is never
        # reused or labelled complete after a copy/publication failure.
        raise ContextPreparationError('Build context preparation could not complete') from error
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', required=True, type=Path)
    parser.add_argument('--runtime-lock', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--python-base-image', required=True)
    parser.add_argument('--runner-base-image', required=True)
    args = parser.parse_args()
    try:
        receipt = prepare(args.artifacts, args.runtime_lock, args.output,
                          args.python_base_image, args.runner_base_image)
    except ContextPreparationError as error:
        print(f'Context preparation failed: {error}', file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
