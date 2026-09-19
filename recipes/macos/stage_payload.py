"""Extract and verify one new recipe payload inside the owned guest."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile


def stage(root, stream):
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    names = set()
    with tarfile.open(fileobj=stream, mode='r|') as package:
        for item in package:
            relative = Path(item.name)
            if (not (item.isfile() or item.isdir()) or relative.is_absolute()
                    or '..' in relative.parts or item.name in names):
                raise ValueError('Invalid or duplicate payload member')
            names.add(item.name)
            package.extract(item, root, filter='data')
    for directory, _, files in os.walk(root):
        Path(directory).chmod(0o755)
        for name in files:
            path = Path(directory) / name
            path.chmod(0o644)
            os.chown(path, 0, 0)
    manifest = json.loads((root / 'PAYLOAD.json').read_text())
    for name, pin in manifest.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid manifest path')
        path = root / relative
        with path.open('rb') as source:
            actual = hashlib.file_digest(source, 'sha256').hexdigest()
        if path.stat().st_size != pin['bytes'] or actual != pin['sha256']:
            raise ValueError('Payload digest mismatch: ' + name)
    return {'verified_files': len(manifest), 'credentials_transferred': False}


if __name__ == '__main__':
    print(json.dumps(stage(Path(sys.argv[1]), sys.stdin.buffer)))
