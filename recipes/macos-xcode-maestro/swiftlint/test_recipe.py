import hashlib
import importlib.util
from pathlib import Path
import stat
import zipfile

import pytest

SPEC = importlib.util.spec_from_file_location('swiftlint_install', Path(__file__).with_name('install.py'))
recipe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recipe)


def archive(tmp_path, extra=None):
    path = tmp_path / 'payload.zip'
    members = {'swiftlint': b'fixture-executable', 'LICENSE': b'fixture-license'}
    with zipfile.ZipFile(path, 'w') as package:
        for name, raw in members.items():
            package.writestr(name, raw)
        if extra:
            package.writestr(extra, b'unexpected')
    pins = {'archive': {'bytes': path.stat().st_size, 'sha256': recipe.digest(path.read_bytes())},
            'members': {name: {'bytes': len(raw), 'sha256': recipe.digest(raw),
                              'mode': '0755' if name == 'swiftlint' else '0644'} for name, raw in members.items()}}
    return path, pins


def test_archive_lock_and_each_extracted_member(tmp_path):
    path, pins = archive(tmp_path)
    assert recipe.verified_members(path, pins)['LICENSE'] == b'fixture-license'
    pins['members']['swiftlint']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='digest'):
        recipe.verified_members(path, pins)


@pytest.mark.parametrize('extra', ['../escape', 'extra', 'swiftlint'])
def test_exact_archive_closure(tmp_path, extra):
    path, pins = archive(tmp_path, extra)
    with pytest.raises(ValueError, match='members'):
        recipe.verified_members(path, pins)


def test_archive_hash_and_regular_file(tmp_path):
    path, pins = archive(tmp_path)
    pins['archive']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='digest'):
        recipe.verified_members(path, pins)
    link = tmp_path / 'link'
    link.symlink_to(path)
    with pytest.raises(ValueError, match='regular'):
        recipe.verified_members(link, pins)


def test_permissions_launcher_and_existing_installation(tmp_path, monkeypatch):
    import os
    path, pins = archive(tmp_path)
    prefix, bin_dir = tmp_path / 'tools' / '0.65.1', tmp_path / 'bin'
    # The pytest directory is intentionally private; production checks every parent.
    def isolated_directory(directory):
        directory.mkdir(parents=True, mode=0o755, exist_ok=True)
        directory.chmod(0o755)
    monkeypatch.setattr(recipe, 'protected_directory', isolated_directory)
    previous = os.umask(0o077)
    try:
        result = recipe.install(path, pins, prefix, bin_dir)
    finally:
        os.umask(previous)
    assert stat.S_IMODE(prefix.stat().st_mode) == 0o755
    assert [file['mode'] for file in result['files']] == ['0755', '0644', '0755']
    assert (bin_dir / 'swiftlint').read_text() == f'#!/bin/sh\nexec {prefix}/swiftlint "$@"\n'
    before = {p: p.read_bytes() for p in [prefix / 'swiftlint', prefix / 'LICENSE', bin_dir / 'swiftlint']}
    with pytest.raises(ValueError, match='never overwritten'):
        recipe.install(path, pins, prefix, bin_dir)
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_symlinked_parent_is_rejected(tmp_path):
    link = tmp_path / 'alias'
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        recipe.protected_directory(link)


def report_checker():
    spec = importlib.util.spec_from_file_location('swiftlint_qualification', Path(__file__).with_name('qualify.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_report


def test_actual_pinned_junit_reports_rule_message_not_identifier():
    report = b'''<testsuites name="SwiftLint" failures="0" errors="1" tests="1">
    <testsuite name="SwiftLint"><testcase classname="Formatting Test" name="Invalid.swift">
    <failure message="Force casts should be avoided">Error:Line:2</failure>
    </testcase></testsuite></testsuites>'''
    check = report_checker()
    assert check(report, 2, False) == 1
    with pytest.raises(AssertionError):
        check(report, 0, False)
    with pytest.raises(AssertionError):
        check(report.replace(b'Force casts should be avoided', b'Unrelated error'), 2, False)


def test_empty_clean_report_requires_successful_lint_exit():
    check = report_checker()
    report = b'<testsuites name="SwiftLint" failures="0" errors="0" tests="0"><testsuite/></testsuites>'
    assert check(report, 0, True) == 0
    with pytest.raises(AssertionError):
        check(report, 2, True)
    with pytest.raises(AssertionError):
        check(report, 0, False)
