"""runner-web-stack-install takes its registry bindings from declarations, keeps the user's npm settings, never stops on them."""
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / 'scripts' / 'runner-web-stack-install.sh'
TOKEN = 'example-token-value-0123456789'

STUB = """#!/bin/sh
# Stand-in for corepack, pnpm, node and the Playwright commands: they only record what the helper hands pnpm.
case "$1" in --version) echo 1.0.0; exit 0;; esac
if [ "$(basename "$0")" = pnpm ] && [ "$1" = install ]; then
  if [ -n "${NPM_CONFIG_USERCONFIG:-}" ]; then cp "$NPM_CONFIG_USERCONFIG" "$CAPTURE"; else echo UNSET > "$CAPTURE"; fi
fi
exit 0
"""


@pytest.fixture
def job(tmp_path):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    for name in ('corepack', 'pnpm', 'node', 'playwright-mcp', 'runner-web-playwright-mcp', 'runner-web-screenshot'):
        (bin_dir / name).write_text(STUB)
        (bin_dir / name).chmod(0o755)
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'package.json').write_text('{}')
    (project / 'pnpm-lock.yaml').write_text('lockfileVersion: 9\n')
    home = tmp_path / 'home'
    home.mkdir()
    (home / '.npmrc').write_text('unrelated-setting=kept\n')
    scratch = tmp_path / 'scratch'
    scratch.mkdir()

    def run(extra=None, *, registries_file=None, home_npmrc=True):
        if not home_npmrc:
            (home / '.npmrc').unlink()
        environment = {'PATH': f'{bin_dir}{os.pathsep}/usr/bin:/bin', 'HOME': str(home), 'TMPDIR': str(scratch),
                       'CAPTURE': str(tmp_path / 'captured'),
                       'RUNNER_WEB_STACK_REGISTRIES_FILE': str(registries_file or tmp_path / 'absent'), **(extra or {})}
        result = subprocess.run(['bash', str(SCRIPT), '--project', str(project)], env=environment,
                                capture_output=True, text=True, cwd=tmp_path)
        captured = tmp_path / 'captured'
        return result, captured.read_text() if captured.exists() else None, scratch
    return run


def test_a_declared_binding_is_written_with_its_credential_and_the_user_settings_are_kept(job):
    result, config, scratch = job({'RUNNER_WEB_REGISTRIES': '@example-scope=packages.example.test=EXAMPLE_REGISTRY_TOKEN',
                                   'EXAMPLE_REGISTRY_TOKEN': TOKEN})
    assert result.returncode == 0, result.stderr
    assert 'unrelated-setting=kept' in config
    assert '@example-scope:registry=https://packages.example.test/' in config
    assert f'//packages.example.test/:_authToken={TOKEN}' in config
    assert TOKEN not in result.stdout + result.stderr
    assert 'WARNING' not in result.stderr
    assert list(scratch.iterdir()) == []  # the temporary config is gone


def test_an_empty_credential_variable_warns_by_name_and_the_install_goes_on(job):
    """A second organization's scope with its own variable: nothing of another organization's variable is needed."""
    result, config, _ = job({'RUNNER_WEB_REGISTRIES': '@second-scope=registry.second.example.test=SECOND_REGISTRY_TOKEN'})
    assert result.returncode == 0
    assert 'the credential variable SECOND_REGISTRY_TOKEN for @second-scope is empty' in result.stderr
    assert '@second-scope:registry=https://registry.second.example.test/' in config
    assert '_authToken' not in config and 'unrelated-setting=kept' in config


def test_two_bindings_each_use_their_own_variable(job):
    result, config, _ = job({'RUNNER_WEB_REGISTRIES': '@one=one.example.test=ONE_TOKEN @two=two.example.test:8443/npm=TWO_TOKEN @three=three.example.test',
                             'ONE_TOKEN': 'one-value', 'TWO_TOKEN': 'two-value'})
    assert result.returncode == 0 and result.stderr == ''
    assert '//one.example.test/:_authToken=one-value' in config
    assert '//two.example.test:8443/npm/:_authToken=two-value' in config
    assert '@three:registry=https://three.example.test/' in config and 'three.example.test/:_authToken' not in config
    assert 'one-value' not in result.stdout + result.stderr and 'two-value' not in result.stdout + result.stderr


def test_the_bindings_can_come_from_the_image_owned_file(job, tmp_path):
    listing = tmp_path / 'registries'
    listing.write_text('@example-scope=packages.example.test=EXAMPLE_REGISTRY_TOKEN\n')
    result, config, _ = job({'EXAMPLE_REGISTRY_TOKEN': TOKEN}, registries_file=listing)
    assert result.returncode == 0 and result.stderr == ''
    assert f'//packages.example.test/:_authToken={TOKEN}' in config


def test_with_no_declaration_the_jobs_own_npm_configuration_is_used_and_the_install_warns(job):
    result, config, scratch = job()
    assert result.returncode == 0
    assert config == 'UNSET\n'  # the helper replaced nothing
    assert 'no registry binding is declared' in result.stderr
    assert list(scratch.iterdir()) == []


def test_the_jobs_own_user_config_variable_is_kept_when_nothing_is_declared(job, tmp_path):
    own = tmp_path / 'own-npmrc'
    own.write_text('from-the-job=1\n')
    result, config, _ = job({'NPM_CONFIG_USERCONFIG': str(own)})
    assert result.returncode == 0 and config == 'from-the-job=1\n'


def test_a_malformed_entry_warns_and_its_siblings_are_used(job, tmp_path):
    (tmp_path / 'matched').write_text('')
    result, config, _ = job({'RUNNER_WEB_REGISTRIES': 'not-an-entry @Bad=host.example.test @ok=ok.example.test=OK_TOKEN @x=h.example.test=1BAD * @y=h.test=A=B',
                             'OK_TOKEN': 'ok-value'}, home_npmrc=False)
    assert result.returncode == 0
    assert result.stderr.count('ignored a registry entry') == 5
    assert '@ok:registry=https://ok.example.test/' in config and '_authToken=ok-value' in config
    assert 'unrelated' not in config


def test_the_file_the_planner_tool_writes_is_the_file_the_helper_reads(job, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('plan_inputs', Path(__file__).resolve().parents[1] / 'common' / 'plan-inputs.py')
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    listing = tmp_path / 'etc' / 'registries'
    written = tool.write_registries('@example-scope=packages.example.test=EXAMPLE_REGISTRY_TOKEN bad', listing)
    assert written['status'] == 'ok' and len(written['warnings']) == 1
    result, config, _ = job({'EXAMPLE_REGISTRY_TOKEN': TOKEN}, registries_file=listing)
    assert result.returncode == 0 and result.stderr == ''
    assert f'//packages.example.test/:_authToken={TOKEN}' in config and 'unrelated-setting=kept' in config


def test_the_script_carries_no_organization_scope_host_or_credential_variable():
    text = SCRIPT.read_text()
    for word in ('@uxmaltech', 'npm.pkg.github.com', 'STOREFRONT', 'enviaflores'):
        assert word not in text
