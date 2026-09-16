"""Focused archive and clone-mechanics checks, without a VM or SDK execution."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
import zipfile

RECIPE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, RECIPE / (name + '.py'))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


install = module('install')
launcher = module('launcher')


class ArchiveTests(unittest.TestCase):
    def archive(self, root, extra_name, payload=b'invalid'):
        path = root / 'fixture.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('flutter/bin/cache/flutter.version.json', json.dumps({
                'frameworkRevision': 'test-revision', 'dartSdkVersion': 'test-dart'}))
            archive.writestr(extra_name, payload)
        pins = {'archive': {'bytes': path.stat().st_size, 'sha256': install.sha_file(path)},
            'flutter_revision': 'test-revision', 'dart_version': 'test-dart'}
        return path, pins

    def test_parent_escape_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            path, pins = self.archive(Path(directory), 'flutter/../../escape')
            with self.assertRaisesRegex(ValueError, 'archive path'):
                install.inspect_archive(path, pins)
            self.assertFalse((Path(directory).parent / 'escape').exists())

    def test_digest_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, pins = self.archive(Path(directory), 'flutter/README.md')
            with path.open('ab') as stream:
                stream.write(b'tampered')
            with self.assertRaisesRegex(ValueError, 'official release pin'):
                install.inspect_archive(path, pins)

    def test_contained_relative_link_is_retained_in_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            item = zipfile.ZipInfo('flutter/link')
            item.create_system = 3
            item.external_attr = 0o120777 << 16
            path, pins = self.archive(Path(directory), item, b'bin/cache/flutter.version.json')
            inspection = install.inspect_archive(path, pins)
            self.assertEqual(inspection['symlinks'], 1)

    def test_external_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            item = zipfile.ZipInfo('flutter/link')
            item.create_system = 3
            item.external_attr = 0o120777 << 16
            path, pins = self.archive(Path(directory), item, b'../../outside')
            with self.assertRaisesRegex(ValueError, 'symlink escapes'):
                install.inspect_archive(path, pins)

    def test_machine_json_keeps_stderr_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'version.log'
            command = [sys.executable, '-c', 'import sys;print("{\\"version\\": 1}");print("warning",file=sys.stderr)']
            receipt = install.run(command, {'PATH': '/usr/bin:/bin'}, root, log, 10, separate_stderr=True)
            self.assertEqual(json.loads(log.read_bytes()), {'version': 1})
            self.assertEqual(Path(receipt['stderr_log']).read_text().strip(), 'warning')


@unittest.skipUnless(platform.system() == 'Darwin', 'APFS clonefile requires Darwin')
class CloneTests(unittest.TestCase):
    def test_clone_is_writable_without_changing_readonly_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / 'seed'
            seed.mkdir()
            payload = seed / 'payload'
            payload.write_bytes(b'sealed input')
            payload.chmod(0o444)
            (seed / 'alias').symlink_to('payload')
            seed.chmod(0o555)
            try:
                count = launcher.clone_tree(seed, root / 'clone')
                self.assertEqual(count, 1)
                copy = root / 'clone/payload'
                self.assertEqual(copy.stat().st_uid, os.geteuid())
                self.assertNotEqual(copy.stat().st_ino, payload.stat().st_ino)
                copy.write_bytes(b'private modification')
                self.assertEqual(payload.read_bytes(), b'sealed input')
                self.assertEqual(os.readlink(root / 'clone/alias'), 'payload')
                self.assertEqual(payload.stat().st_mode & 0o777, 0o444)
            finally:
                seed.chmod(0o755)


if __name__ == '__main__':
    unittest.main()
