"""Relocate a generated Python console in a fresh image payload, preserving its input."""
from pathlib import Path
import ast
import base64
import configparser
import csv
import hashlib
import io
import os
import re
import shutil
import stat


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare_runtime(runtime, destination, installer, *, canonical_path, python_destination,
                    console_name, distribution_name, entrypoint, python_version):
    """Relocate the generated CLI in a fresh copy; never rewrite input artifacts."""
    require(all(re.fullmatch(r'[A-Za-z0-9_.-]+', item) for item in
                (console_name, distribution_name, python_version)), 'native-console-identity-invalid')
    module_name, function_name = entrypoint.split(':')
    runtime = canonical_path(runtime)
    original_hash = installer.tree_hash(runtime)

    def read(relative, maximum=64 * 1024):
        path = canonical_path(runtime / relative)
        info = path.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_size <= maximum,
                'native-console-file-required')
        return path.read_bytes(), stat.S_IMODE(info.st_mode)

    console = Path('bin') / console_name
    original, mode = read(console)
    require(mode & 0o111 and original.startswith(b'#!') and b'\n' in original,
            'native-python-console-required')
    body = original.split(b'\n', 1)[1]
    try:
        syntax = ast.parse(body.decode('utf-8'))
    except (SyntaxError, UnicodeError):
        raise ValueError('native-python-console-body-invalid') from None
    require(any(isinstance(node, ast.ImportFrom) and node.module == module_name
                and any(alias.name == function_name for alias in node.names) for node in ast.walk(syntax)),
            'native-python-console-entrypoint-required')
    site = Path('lib') / ('python' + python_version) / 'site-packages'
    metadata = list((runtime / site).glob(distribution_name + '-*.dist-info'))
    require(len(metadata) == 1, 'native-cli-metadata-required')
    metadata = metadata[0].relative_to(runtime)
    entries, _ = read(metadata / 'entry_points.txt')
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(entries.decode('utf-8'))
    except (configparser.Error, UnicodeError):
        raise ValueError('native-cli-entrypoint-metadata-invalid') from None
    require(parser.get('console_scripts', console_name, fallback=None) == entrypoint,
            'native-cli-entrypoint-metadata-invalid')
    interpreter = str(python_destination / 'bin' / ('python' + python_version))
    relocated = ('#!' + interpreter + '\n').encode('utf-8') + body
    changes = []
    replacements = []

    def replacement(relative, before, after, permissions):
        if before != after:
            replacements.append((relative, after, permissions))
            changes.append({'path': str(relative), 'before_sha256': hashlib.sha256(before).hexdigest(),
                            'after_sha256': hashlib.sha256(after).hexdigest(),
                            'before_bytes': len(before), 'after_bytes': len(after)})

    replacement(console, original, relocated, mode)
    record = metadata / 'RECORD'
    record_bytes, record_mode = read(record, 1024 * 1024)
    try:
        rows = list(csv.reader(io.StringIO(record_bytes.decode('utf-8'))))
    except (csv.Error, UnicodeError):
        raise ValueError('native-cli-record-invalid') from None
    require(all(len(row) == 3 for row in rows), 'native-cli-record-invalid')
    # pip records generated scripts; a verified wheel RECORD may omit them.
    # Keep that distinction and do not invent a wheel-owned console entry.
    matches = [row for row in rows if row[0] == '../../../bin/' + console_name]
    require(len(matches) <= 1, 'native-cli-record-invalid')
    if matches:
        digest = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(relocated).digest()).decode().rstrip('=')
        updated = [matches[0][0], digest, str(len(relocated))]
        if matches[0] != updated:
            matches[0][:] = updated
            stream = io.StringIO(newline='')
            csv.writer(stream, lineterminator='\r\n' if b'\r\n' in record_bytes else '\n').writerows(rows)
            replacement(record, record_bytes, stream.getvalue().encode('utf-8'), record_mode)
    prepared = runtime
    if replacements:
        require(not destination.resolve().is_relative_to(runtime), 'native-runtime-output-must-be-separate')
        shutil.copytree(runtime, destination, symlinks=True)
        require(installer.tree_hash(destination) == original_hash, 'native-runtime-copy-changed')
        for relative, data, permissions in replacements:
            path = destination / relative
            temporary = path.with_name('.' + path.name + '.relocating')
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                with os.fdopen(fd, 'wb', closefd=False) as output:
                    output.write(data)
                    output.flush()
                    os.fsync(fd)
                os.fchmod(fd, permissions)
            finally:
                os.close(fd)
            os.replace(temporary, path)
        prepared = destination
    require(installer.tree_hash(runtime) == original_hash, 'native-runtime-input-changed')
    return prepared, {'schema_version': 1, 'status': 'copied-and-relocated' if changes else 'already-relocated',
                      'source': str(runtime), 'source_sha256': original_hash,
                      'prepared': str(prepared), 'prepared_sha256': installer.tree_hash(prepared),
                      'interpreter': interpreter, 'changes': changes, 'originals_preserved': True}

