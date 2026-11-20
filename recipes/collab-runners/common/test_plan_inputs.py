"""Plan-time inputs: a journey binding is rendered or kept, never a placeholder; aliases are linked or skipped."""
import importlib.util
import json
import os
import stat
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('plan_inputs', Path(__file__).with_name('plan-inputs.py'))
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)
RECIPES = Path(__file__).resolve().parents[1]

# Fixtures never use a real organization: example-org / example-* only.
DRIVER = {'schema_version': 1, 'repository': 'example-org/example-prior', 'profile': 'example-prior-profile',
          'backend': 'linux-docker', 'driver': 'android-maestro', 'validator': 'scripts/prior-validate.py',
          'maximum_seconds': 7200}
EXECUTION = {'schema_version': 2, 'repository': 'example-org/example-prior', 'profile': 'example-prior-profile',
             'pack_root': '/opt/collab/repo-pack', 'driver': '/opt/ai-repo-resources/journey-driver.json',
             'capability': 'repo.journey.ios.v2'}
INPUTS = ['--repository', 'example-org/example-app', '--profile', 'example-app-profile',
          '--validator', 'scripts/validate-maestro.py']


def prior(tmp_path, document=DRIVER, name='journey-driver.json'):
    path = tmp_path / name
    path.write_text(json.dumps(document, indent=2) + '\n')
    return path


def render(capsys, *arguments, environment=None):
    status = tool.main(list(arguments), environment={} if environment is None else environment)
    captured = capsys.readouterr()
    return status, json.loads(captured.out.splitlines()[-1]), captured.err


def test_all_inputs_rendered_over_the_prior_binding_keep_its_constants(tmp_path, capsys):
    fallback = prior(tmp_path)
    output = tmp_path / 'out' / 'journey-driver.json'
    status, result, err = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(output), *INPUTS)
    assert status == 0 and result['status'] == 'rendered' and result['source'] == 'plan-inputs'
    assert result['warnings'] == [] and err == ''
    document = json.loads(output.read_text())
    assert document == {**DRIVER, 'repository': 'example-org/example-app', 'profile': 'example-app-profile',
                        'validator': 'scripts/validate-maestro.py'}
    assert list(document) == list(DRIVER)
    assert stat.S_IMODE(output.stat().st_mode) == 0o644
    assert not list(output.parent.glob('.*.part'))


def test_no_inputs_keep_the_prior_binding_byte_for_byte_and_warn(tmp_path, capsys):
    fallback = prior(tmp_path)
    before = fallback.read_bytes()
    status, result, err = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(fallback))
    assert status == 0 and result['status'] == 'kept' and result['source'] == 'prior-verified'
    assert 'keeping the prior verified binding' in result['warnings'][0]
    assert err.startswith('WARNING: ')
    assert fallback.read_bytes() == before


def test_the_prior_binding_is_copied_to_another_output_when_no_inputs_are_given(tmp_path, capsys):
    fallback, output = prior(tmp_path), tmp_path / 'rendered.json'
    status, result, _ = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(output))
    assert status == 0 and result['status'] == 'kept'
    assert json.loads(output.read_text()) == DRIVER


def test_a_partial_set_is_not_mixed_into_the_prior_binding(tmp_path, capsys):
    fallback = prior(tmp_path)
    before = fallback.read_bytes()
    status, result, _ = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(fallback),
                               '--repository', 'example-org/example-app')
    assert status == 0 and result['status'] == 'kept'
    assert 'missing: profile, validator' in result['warnings'][0]
    assert fallback.read_bytes() == before


@pytest.mark.parametrize('field, value', [
    ('--repository', '<organization>/<repository>'),
    ('--repository', 'example-org'),
    ('--repository', 'a/b/c'),
    ('--profile', 'two\nlines'),
    ('--validator', '/abs/validate.py'),
    ('--validator', 'scripts/../validate.py'),
    ('--validator', 'scripts/validate.sh'),
    ('--validator', 'scripts\\validate.py'),
])
def test_a_placeholder_or_malformed_value_is_never_written(tmp_path, capsys, field, value):
    fallback = prior(tmp_path)
    before = fallback.read_bytes()
    arguments = dict(zip(INPUTS[::2], INPUTS[1::2]))
    arguments[field] = value
    flat = [item for pair in arguments.items() for item in pair]
    status, result, _ = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(fallback), *flat)
    assert status == 0 and result['status'] == 'kept'
    assert f'invalid: {field[2:]}' in result['warnings'][0]
    assert fallback.read_bytes() == before


def test_a_document_without_a_validator_needs_only_the_facts_it_binds(tmp_path, capsys):
    fallback = prior(tmp_path, EXECUTION, 'journey-execution.json')
    output = tmp_path / 'execution.json'
    status, result, _ = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(output),
                               '--repository', 'example-org/example-app', '--profile', 'example-app-profile',
                               '--validator', 'scripts/ignored.py')
    assert status == 0 and result['status'] == 'rendered'
    assert json.loads(output.read_text()) == {**EXECUTION, 'repository': 'example-org/example-app',
                                               'profile': 'example-app-profile'}


def test_the_inputs_can_come_from_the_build_arguments_in_the_environment(tmp_path, capsys):
    fallback = prior(tmp_path)
    environment = {'RUNNER_JOURNEY_REPOSITORY': 'example-org/example-env', 'RUNNER_JOURNEY_PROFILE': 'example-env-profile',
                   'RUNNER_JOURNEY_VALIDATOR': 'tools/validate.py'}
    status, result, _ = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(fallback),
                               environment=environment)
    assert status == 0 and result['status'] == 'rendered'
    assert json.loads(fallback.read_text())['repository'] == 'example-org/example-env'


def test_an_unreadable_prior_binding_writes_nothing_and_still_succeeds(tmp_path, capsys):
    missing = tmp_path / 'absent.json'
    output = tmp_path / 'out.json'
    status, result, err = render(capsys, 'journey', '--fallback', str(missing), '--output', str(output), *INPUTS)
    assert status == 0 and result['status'] == 'not_done'
    assert 'cannot be read' in result['warnings'][0] and 'WARNING:' in err
    assert not output.exists()
    broken = tmp_path / 'broken.json'
    broken.write_text('[1, 2]')
    status, result, _ = render(capsys, 'journey', '--fallback', str(broken), '--output', str(output), *INPUTS)
    assert status == 0 and result['status'] == 'not_done' and not output.exists()


def test_an_output_that_cannot_be_written_is_a_warning(tmp_path, capsys):
    fallback = prior(tmp_path)
    blocked = tmp_path / 'file'
    blocked.write_text('x')
    status, result, _ = render(capsys, 'journey', '--fallback', str(fallback), '--output', str(blocked / 'out.json'), *INPUTS)
    assert status == 0 and result['status'] == 'not_done' and 'cannot be written' in result['warnings'][0]


@pytest.mark.parametrize('arguments', [[], ['bogus'], ['journey'], ['journey', '--fallback', 'x'], ['aliases', '--unknown']])
def test_a_malformed_command_line_warns_and_exits_zero(capsys, arguments):
    status, result, err = render(capsys, *arguments)
    assert status == 0 and result['status'] == 'not_done'
    assert 'invalid options' in result['warnings'][0] and 'WARNING:' in err


def helper(root, name='runner-tool', executable=True):
    path = root / 'usr' / 'local' / 'bin' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\n')
    path.chmod(0o755 if executable else 0o644)
    return path


def test_an_alias_is_a_link_to_the_neutral_helper(tmp_path, capsys):
    helper(tmp_path)
    status, result, err = render(capsys, 'aliases', '--root', str(tmp_path),
                                 '--map', '/usr/local/bin/former-tool=runner-tool')
    assert status == 0 and result['status'] == 'ok' and result['warnings'] == [] and err == ''
    link = tmp_path / 'usr/local/bin/former-tool'
    assert link.is_symlink() and os.readlink(link) == '/usr/local/bin/runner-tool'
    # Running it again is not an error and changes nothing.
    status, again, _ = render(capsys, 'aliases', '--root', str(tmp_path), '--map', '/usr/local/bin/former-tool=runner-tool')
    assert status == 0 and again['status'] == 'ok' and again['warnings'] == []


def test_a_bad_alias_warns_and_its_siblings_are_still_linked(tmp_path, capsys):
    helper(tmp_path)
    helper(tmp_path, 'plain', executable=False)
    existing = tmp_path / 'usr/local/bin/taken'
    existing.write_text('keep me')
    spec = ' '.join([
        '/usr/local/bin/one=runner-tool',          # valid
        '/etc/shadow=runner-tool',                 # outside /usr/local
        '/usr/local/../etc/x=runner-tool',         # traversal
        'no-equals-sign',                          # malformed
        '/usr/local/bin/two=missing-helper',       # helper does not exist
        '/usr/local/bin/three=plain',              # helper is not executable
        '/usr/local/bin/taken=runner-tool',        # would replace a file
        '/usr/local/bin/four=/usr/local/bin/runner-tool',  # valid, absolute target
    ])
    status, result, err = render(capsys, 'aliases', '--root', str(tmp_path), '--map', spec)
    assert status == 0 and result['status'] == 'partial'
    outcomes = {entry['alias']: entry['status'] for entry in result['aliases']}
    assert outcomes['/usr/local/bin/one'] == 'ok' and outcomes['/usr/local/bin/four'] == 'ok'
    assert all(status == 'skipped' for alias, status in outcomes.items()
               if alias not in ('/usr/local/bin/one', '/usr/local/bin/four'))
    assert len(result['warnings']) == 6 and err.count('WARNING:') == 6
    assert existing.read_text() == 'keep me'
    assert not (tmp_path / 'etc').exists()
    assert (tmp_path / 'usr/local/bin/one').is_symlink() and (tmp_path / 'usr/local/bin/four').is_symlink()


def test_a_link_that_points_elsewhere_is_not_replaced(tmp_path, capsys):
    helper(tmp_path)
    link = tmp_path / 'usr/local/bin/former-tool'
    os.symlink('/somewhere/else', link)
    status, result, _ = render(capsys, 'aliases', '--root', str(tmp_path), '--map', '/usr/local/bin/former-tool=runner-tool')
    assert status == 0 and result['status'] == 'partial' and 'was not replaced' in result['warnings'][0]
    assert os.readlink(link) == '/somewhere/else'


def test_no_alias_requested_is_a_note_not_a_warning(tmp_path, capsys):
    status, result, err = render(capsys, 'aliases', '--root', str(tmp_path), '--map', '')
    assert status == 0 and result['status'] == 'none' and result['warnings'] == []
    assert err.startswith('NOTE: ')


def test_the_aliases_come_from_the_build_argument_in_the_environment(tmp_path, capsys):
    helper(tmp_path)
    status, result, _ = render(capsys, 'aliases', '--root', str(tmp_path),
                               environment={'RUNNER_HELPER_ALIASES': '/usr/local/bin/from-env=runner-tool'})
    assert status == 0 and result['status'] == 'ok'
    assert (tmp_path / 'usr/local/bin/from-env').is_symlink()


def test_the_tool_and_the_recipes_that_use_it_carry_no_organization_value():
    text = (RECIPES / 'common' / 'plan-inputs.py').read_text()
    for recipe in ('runner-resolver-android', 'runner-resolver-nuxt-pnpm'):
        dockerfile = (RECIPES / recipe / 'Dockerfile').read_text()
        assert 'plan-inputs.py' in dockerfile
        assert '<organization>' not in dockerfile and '<repository>' not in dockerfile
    assert '<organization>' not in text


@pytest.mark.parametrize('recipe, name', [('runner-resolver-android', 'journey-driver.json'),
                                          ('runner-resolver-ios', 'journey-driver.json'),
                                          ('runner-resolver-ios', 'journey-execution.json')])
def test_the_shipped_prior_binding_is_a_complete_document_without_a_placeholder(recipe, name):
    document = json.loads((RECIPES / recipe / name).read_text())
    for fact in ('repository', 'profile'):
        assert tool.FACTS[fact](document[fact]), (recipe, name, fact)
    if 'validator' in document:
        assert tool.FACTS['validator'](document['validator'])


def pinned_runtime(tmp_path, monkeypatch, declaration=None):
    """The pinned runtime's own modules, with its pack root pointed at a pack that declares the journey."""
    configuration = pytest.importorskip('collab.repo.journeys.configuration')
    docker_journey = pytest.importorskip('collab.repo.journeys.docker_journey')
    journey_jobs = pytest.importorskip('collab.repo.journeys.journey_jobs')
    native_image = pytest.importorskip('collab_runners.contracts.native_image')
    pack = tmp_path / 'pack'
    (pack / 'runners').mkdir(parents=True)
    declaration = {'repository': 'example-org/example-app', 'profile': 'example-app-profile',
                   'validator': 'scripts/validate-maestro.py', 'driver': 'runners/driver.json',
                   'helper': '/usr/local/bin/runner-android-emulator', **(declaration or {})}
    (pack / 'runners' / 'journeys.json').write_text(json.dumps(
        {'schema': 'collab.repo-journeys/v2', 'android': declaration, 'native': declaration}))
    monkeypatch.setattr(configuration, 'pack_root', lambda: pack)
    return docker_journey, journey_jobs, native_image


def test_rendered_bindings_pass_the_pinned_runtimes_own_validation(tmp_path, monkeypatch, capsys):
    """Skipped unless the pinned runtime is importable (PYTHONPATH=<cli>/src:<cli>/providers/runners/src)."""
    docker_journey, journey_jobs, native_image = pinned_runtime(tmp_path, monkeypatch)
    driver = {'schema_version': 1, 'repository': 'example-org/prior', 'profile': 'prior', 'backend': 'linux-docker',
              'driver': 'android-maestro', 'validator': 'scripts/prior.py', 'maximum_seconds': 7200}
    android = tmp_path / 'android.json'
    render(capsys, 'journey', '--fallback', str(prior(tmp_path, driver, 'android-prior.json')), '--output', str(android), *INPUTS)
    monkeypatch.setattr(docker_journey, 'DRIVER', android)
    docker_journey.validate_recipe()  # raises when the image driver differs from the pack's declaration

    ios_driver = {**driver, 'backend': 'macos-tart', 'driver': 'ios-maestro'}
    ios = tmp_path / 'ios.json'
    render(capsys, 'journey', '--fallback', str(prior(tmp_path, ios_driver, 'ios-prior.json')), '--output', str(ios), *INPUTS)
    journey_jobs.driver(json.loads(ios.read_text()))

    execution = {'schema_version': 2, 'repository': 'example-org/prior', 'profile': 'prior', 'pack_root': '/opt/collab/repo-pack',
                 'python': '/opt/collab/runtime/bin/python3.12', 'driver': '/opt/ai-repo-resources/journey-driver.json',
                 'runtime_root': '/opt/collab/runtime', 'capability': 'repo.journey.ios.v2'}
    rendered = tmp_path / 'execution.json'
    render(capsys, 'journey', '--fallback', str(prior(tmp_path, execution, 'execution-prior.json')), '--output', str(rendered), *INPUTS)
    declared = native_image.execution_declaration(json.loads(rendered.read_text()))
    # The selected-repository comparison of prepare_native_image.main, against the repository the pack's agent targets.
    assert declared['repository'] == 'example-org/example-app'
    assert declared['profile'] == journey_jobs.setting('native', 'profile')


def test_the_pinned_runtime_rejects_a_literal_placeholder(tmp_path, monkeypatch):
    """The control of the test above: the check is real, and a placeholder fails it."""
    docker_journey, journey_jobs, native_image = pinned_runtime(tmp_path, monkeypatch)
    placeholder = tmp_path / 'placeholder.json'
    placeholder.write_text(json.dumps({'schema_version': 1, 'repository': '<organization>/<repository>', 'profile': 'x',
                                       'backend': 'linux-docker', 'driver': 'android-maestro',
                                       'validator': 'scripts/validate-maestro.py', 'maximum_seconds': 7200}))
    monkeypatch.setattr(docker_journey, 'DRIVER', placeholder)
    with pytest.raises(Exception):
        docker_journey.validate_recipe()


def test_the_shipped_prior_bindings_pass_the_pinned_runtime_when_the_pack_declares_the_same_values(tmp_path, monkeypatch):
    """The fallback is the binding verified before: with a pack that declares its values it is accepted as shipped."""
    android = json.loads((RECIPES / 'runner-resolver-android' / 'journey-driver.json').read_text())
    docker_journey, journey_jobs, native_image = pinned_runtime(
        tmp_path, monkeypatch, {key: android[key] for key in ('repository', 'profile', 'validator')})
    monkeypatch.setattr(docker_journey, 'DRIVER', RECIPES / 'runner-resolver-android' / 'journey-driver.json')
    docker_journey.validate_recipe()

    ios = json.loads((RECIPES / 'runner-resolver-ios' / 'journey-driver.json').read_text())
    execution = json.loads((RECIPES / 'runner-resolver-ios' / 'journey-execution.json').read_text())
    monkeypatch.undo()
    docker_journey, journey_jobs, native_image = pinned_runtime(
        tmp_path / 'ios', monkeypatch, {key: ios[key] for key in ('repository', 'profile', 'validator')})
    journey_jobs.driver(ios)
    declared = native_image.execution_declaration(execution)
    assert declared['repository'] == ios['repository']
    assert declared['profile'] == journey_jobs.setting('native', 'profile')
    assert declared['driver'] == '/opt/ai-repo-resources/journey-driver.json'
