#!/usr/bin/env python3
"""Install the reviewed archive lock during the Docker build, without latest pins."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen


def verified_archive(item, root, archive_cache=None):
    """Copy and verify bytes, including cache hits, before opening any archive."""
    archive = root / ('download.zip' if item['url'].endswith('.zip') else 'download.tar.gz')
    cached = archive_cache / Path(urlsplit(item['url']).path).name if archive_cache else None
    source = cached.open('rb') if cached and cached.exists() else urlopen(item['url'], timeout=120)
    digest = hashlib.sha256()
    total = 0
    with source, archive.open('xb') as output:
        while chunk := source.read(1024 * 1024):
            total += len(chunk)
            if total > item['size']:
                raise RuntimeError(f"Archive size mismatch: {item['name']}")
            output.write(chunk)
            digest.update(chunk)
    if digest.hexdigest() != item['sha256'] or total != item['size']:
        raise RuntimeError(f"Archive integrity mismatch: {item['name']}")
    return archive


def install(lock, archive_cache=None):
    for item in lock['archives']:
        destination = Path(item['destination'])
        if destination.exists():
            raise RuntimeError(f"Refusing to replace existing toolchain: {destination}")
        with tempfile.TemporaryDirectory(prefix='android-toolchain-') as temporary:
            root = Path(temporary)
            archive = verified_archive(item, root, archive_cache)
            extracted = root / 'extracted'
            extracted.mkdir()
            if archive.suffix == '.zip':
                subprocess.run(['unzip', '-q', str(archive), '-d', str(extracted)], check=True)
            else:
                subprocess.run(['tar', '--no-same-owner', '-xzf', str(archive), '-C', str(extracted)], check=True)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(extracted / item['archive_root']), destination)
            print(f"Installed {item['name']} {item['version']} sha256:{item['sha256']}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-cache', type=Path)
    parser.add_argument('--lock', type=Path, default=Path('/opt/ef-storefront-android/toolchain-lock.json'))
    arguments = parser.parse_args(argv)
    install(json.loads(arguments.lock.read_text()), arguments.archive_cache)


if __name__ == '__main__':
    main()
