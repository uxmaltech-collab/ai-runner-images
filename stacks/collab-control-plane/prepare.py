#!/usr/bin/env python3
"""Prepare an image context using the separately installed, pinned Collab runtime."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from collab.distribution import verify_release


def prepare(artifacts: Path, expected_lock: Path, output: Path, python_base: str, runner_base: str) -> dict:
    manifest = verify_release(artifacts)
    lock = json.loads(expected_lock.read_text())
    if lock.get('schema') != 'collab.runtime-lock/v1' or lock.get('runtime') != manifest['runtime']:
        raise ValueError('Expected runtime lock differs from the supplied release')
    if any(not re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', image) for image in (python_base, runner_base)):
        raise ValueError('Python and runner-tool base images require immutable digests')
    if output.exists():
        raise ValueError('Build context must be a new directory')
    output.mkdir(parents=True)
    release = output / 'collab-release'
    release.mkdir()
    for name in [entry['name'] for entry in manifest['files']] + ['release-manifest.json', 'SHA256SUMS']:
        shutil.copyfile(artifacts / name, release / name)
    shutil.copyfile(Path(__file__).with_name('Dockerfile'), output / 'Dockerfile')
    receipt = {'schema': 'collab.image-context/v1', 'runtime': manifest['runtime'],
               'python_base_image': python_base, 'runner_base_image': runner_base, 'image_build': 'not-run',
               'image_publication': 'not-run', 'host_installation': 'not-run',
               'files': {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted(output.rglob('*')) if path.is_file()}}
    (output / 'context-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', required=True, type=Path)
    parser.add_argument('--runtime-lock', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--python-base-image', required=True)
    parser.add_argument('--runner-base-image', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.artifacts, args.runtime_lock, args.output, args.python_base_image, args.runner_base_image), indent=2))


if __name__ == '__main__':
    main()
