"""Focused archive and clone-mechanics checks, without a VM or SDK execution."""
import importlib.util
import ctypes
import json
import os
from pathlib import Path
import platform
import stat
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
repair = module('repair-symlink-modes')


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
    @unittest.skipUnless(os.getuid() == 0, 'Dropping to the guest UID requires root')
    def test_sealed_symlinks_are_readable_and_cloneable_by_nonroot(self):
        # Load the native library before dropping privileges in the child.
        ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
        with tempfile.TemporaryDirectory(prefix='flutter-symlink-regression-', dir='/private/tmp') as directory:
            root = Path(directory)
            root.chmod(0o755)
            seed = root / 'seed'
            (seed / 'Versions/A').mkdir(parents=True)
            payload = seed / 'Versions/A/payload'
            payload.write_bytes(b'root-owned sealed bytes')
            payload.chmod(0o444)
            (seed / 'Versions/Current').symlink_to('A')
            (seed / 'alias').symlink_to('Versions/Current/payload')
            for link in (seed / 'Versions/Current', seed / 'alias'):
                os.chmod(link, 0o700, follow_symlinks=False)
            for path in (seed, seed / 'Versions', seed / 'Versions/A'):
                path.chmod(0o555)
            destination = root / 'user'
            destination.mkdir(mode=0o700)
            os.chown(destination, 504, 504)

            def child_clone(name):
                read_fd, write_fd = os.pipe()
                pid = os.fork()
                if pid == 0:
                    os.close(read_fd)
                    try:
                        os.setgroups([])
                        os.setgid(504)
                        os.setuid(504)
                        count = launcher.clone_tree(seed, destination / name)
                        copied = destination / name / 'Versions/A/payload'
                        copied.write_bytes(b'only the private clone changed')
                        result = {'passed': True, 'uid': os.geteuid(), 'files': count,
                            'target': os.readlink(destination / name / 'alias')}
                    except Exception as error:
                        result = {'passed': False, 'error': str(error)}
                    os.write(write_fd, json.dumps(result).encode())
                    os.close(write_fd)
                    os._exit(0)
                os.close(write_fd)
                with os.fdopen(read_fd, 'rb') as stream:
                    result = json.loads(stream.read())
                _, status = os.waitpid(pid, 0)
                self.assertEqual(os.waitstatus_to_exitcode(status), 0)
                return result

            try:
                failed = child_clone('before')
                self.assertFalse(failed['passed'])
                self.assertIn('Permission denied', failed['error'])
                entries = install.inventory_and_seal(seed)
                links = [entry for entry in entries if entry['kind'] == 'symlink']
                self.assertEqual(len(links), 2)
                self.assertTrue(all(entry['mode'] == 0o555 for entry in links))
                verified, files, _ = repair.verify_seed(seed, entries)
                self.assertEqual((len(verified), files), (2, 1))
                passed = child_clone('after')
                self.assertTrue(passed['passed'], passed)
                self.assertEqual((passed['uid'], passed['files']), (504, 1))
                self.assertEqual(passed['target'], 'Versions/Current/payload')
                self.assertEqual(payload.read_bytes(), b'root-owned sealed bytes')
                self.assertEqual(stat.S_IMODE(payload.stat().st_mode), 0o444)
                self.assertEqual(payload.stat().st_uid, 0)
                payload.write_bytes(b'unexpected tampering')
                with self.assertRaisesRegex(ValueError, 'differs from the preserved manifest'):
                    repair.verify_seed(seed, entries)
            finally:
                for path in (seed, seed / 'Versions', seed / 'Versions/A'):
                    path.chmod(0o755)

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
