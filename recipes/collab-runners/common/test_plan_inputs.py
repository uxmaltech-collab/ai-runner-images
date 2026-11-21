"""Plan-time inputs: a journey binding is rendered from its template or not written, never a placeholder or another organization's; aliases, markers and registries are applied or skipped; only another artifact stops."""
import importlib.util
import json
import os
import re
import stat
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('plan_inputs', Path(__file__).with_name('plan-inputs.py'))
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)
RECIPES = Path(__file__).resolve().parents[1]

# Fixtures never use a real organization: example-org / example-* only. A template binds a fact with null.
DRIVER = {'schema_version': 1, 'repository': None, 'profile': None,
          'backend': 'linux-docker', 'driver': 'android-maestro', 'validator': None,
          'maximum_seconds': 7200}
EXECUTION = {'schema_version': 2, 'repository': None, 'profile': None,
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


def test_all_inputs_rendered_into_the_template_keep_its_constants(tmp_path, capsys):
    template = prior(tmp_path)
    output = tmp_path / 'out' / 'journey-driver.json'
    status, result, err = render(capsys, 'journey', '--template', str(template), '--output', str(output), *INPUTS)
    assert status == 0 and result['status'] == 'rendered' and result['source'] == 'plan-inputs'
    assert result['warnings'] == [] and err == ''
    document = json.loads(output.read_text())
    assert document == {**DRIVER, 'repository': 'example-org/example-app', 'profile': 'example-app-profile',
                        'validator': 'scripts/validate-maestro.py'}
    assert list(document) == list(DRIVER)
    assert stat.S_IMODE(output.stat().st_mode) == 0o644
    assert not list(output.parent.glob('.*.part'))


def test_no_inputs_write_no_binding_and_warn_and_the_build_goes_on(tmp_path, capsys):
    template = prior(tmp_path)
    output = tmp_path / 'out' / 'journey-driver.json'
    before = template.read_bytes()
    status, result, err = render(capsys, 'journey', '--template', str(template), '--output', str(output))
    assert status == 0 and result['status'] == 'not_done' and result['source'] == 'none'
    assert 'no journey binding was resolved' in result['warnings'][0] and 'built without one' in result['warnings'][0]
    assert err.startswith('WARNING: ')
    assert not output.exists() and template.read_bytes() == before


def test_a_binding_already_in_the_output_is_not_replaced_by_a_failed_render(tmp_path, capsys):
    template = prior(tmp_path)
    output = tmp_path / 'journey-driver.json'
    output.write_text('{"kept": true}\n')
    status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(output))
    assert status == 0 and result['status'] == 'not_done'
    assert output.read_text() == '{"kept": true}\n'


def test_a_partial_set_is_not_written(tmp_path, capsys):
    template = prior(tmp_path)
    output = tmp_path / 'out.json'
    status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(output),
                               '--repository', 'example-org/example-app')
    assert status == 0 and result['status'] == 'not_done'
    assert 'missing: profile, validator' in result['warnings'][0]
    assert not output.exists()


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
    template = prior(tmp_path)
    output = tmp_path / 'out.json'
    arguments = dict(zip(INPUTS[::2], INPUTS[1::2]))
    arguments[field] = value
    flat = [item for pair in arguments.items() for item in pair]
    status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(output), *flat)
    assert status == 0 and result['status'] == 'not_done'
    assert f'invalid: {field[2:]}' in result['warnings'][0]
    assert not output.exists()


def test_a_document_without_a_validator_needs_only_the_facts_it_binds(tmp_path, capsys):
    template = prior(tmp_path, EXECUTION, 'journey-execution.json')
    output = tmp_path / 'execution.json'
    status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(output),
                               '--repository', 'example-org/example-app', '--profile', 'example-app-profile',
                               '--validator', 'scripts/ignored.py')
    assert status == 0 and result['status'] == 'rendered'
    assert json.loads(output.read_text()) == {**EXECUTION, 'repository': 'example-org/example-app',
                                               'profile': 'example-app-profile'}


IMAGE_BUILD = RECIPES / 'runner-resolver-ios' / 'image-build.json'


def test_the_image_declaration_is_rendered_pointing_at_the_rendered_driver_never_at_a_template(tmp_path, capsys):
    """The native preparation reads `driver` of the rendered image declaration: it must name the rendered driver."""
    template = json.loads(IMAGE_BUILD.read_text())
    assert template['driver'] is None and template['profile'] is None
    plan = tmp_path / 'plan'
    driver = plan / 'journey-driver.json'
    status, result, _ = render(capsys, 'journey', '--template', str(RECIPES / 'runner-resolver-ios' / 'journey-driver.json'),
                               '--output', str(driver), *INPUTS)
    assert status == 0 and result['status'] == 'rendered'
    image = plan / 'image-build.json'
    status, result, _ = render(capsys, 'journey', '--template', str(IMAGE_BUILD), '--output', str(image), *INPUTS,
                               '--driver', str(driver))
    assert status == 0 and result['status'] == 'rendered'
    rendered = json.loads(image.read_text())
    assert rendered == {**template, 'profile': 'example-app-profile', 'driver': str(driver)}
    followed = json.loads(Path(rendered['driver']).read_text())
    assert followed['repository'] == 'example-org/example-app' and followed['validator'] == 'scripts/validate-maestro.py'
    assert not any(value is None for value in followed.values())


def test_the_image_declaration_without_a_rendered_driver_is_not_written(tmp_path, capsys):
    image = tmp_path / 'image-build.json'
    status, result, _ = render(capsys, 'journey', '--template', str(IMAGE_BUILD), '--output', str(image), *INPUTS)
    assert status == 0 and result['status'] == 'not_done' and 'missing: driver' in result['warnings'][0]
    assert not image.exists()


@pytest.mark.parametrize('value', ['recipes/x/journey-driver.json.tmpl', '../driver.json', '/a/../driver.json', 'a\\b.json', ''])
def test_an_invalid_driver_path_is_never_written(tmp_path, capsys, value):
    image = tmp_path / 'image-build.json'
    status, result, _ = render(capsys, 'journey', '--template', str(IMAGE_BUILD), '--output', str(image), *INPUTS, '--driver', value)
    assert status == 0 and result['status'] == 'not_done' and not image.exists()


def test_the_inputs_can_come_from_the_build_arguments_in_the_environment(tmp_path, capsys):
    template = prior(tmp_path)
    output = tmp_path / 'out.json'
    environment = {'RUNNER_JOURNEY_REPOSITORY': 'example-org/example-env', 'RUNNER_JOURNEY_PROFILE': 'example-env-profile',
                   'RUNNER_JOURNEY_VALIDATOR': 'tools/validate.py'}
    status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(output),
                               environment=environment)
    assert status == 0 and result['status'] == 'rendered'
    assert json.loads(output.read_text())['repository'] == 'example-org/example-env'


def test_an_unreadable_template_writes_nothing_and_still_succeeds(tmp_path, capsys):
    missing = tmp_path / 'absent.json'
    output = tmp_path / 'out.json'
    status, result, err = render(capsys, 'journey', '--template', str(missing), '--output', str(output), *INPUTS)
    assert status == 0 and result['status'] == 'not_done'
    assert 'cannot be read' in result['warnings'][0] and 'WARNING:' in err
    assert not output.exists()
    broken = tmp_path / 'broken.json'
    broken.write_text('[1, 2]')
    status, result, _ = render(capsys, 'journey', '--template', str(broken), '--output', str(output), *INPUTS)
    assert status == 0 and result['status'] == 'not_done' and not output.exists()
    plain = prior(tmp_path, {'schema_version': 1, 'driver': 'x'}, 'plain.json')
    status, result, _ = render(capsys, 'journey', '--template', str(plain), '--output', str(output), *INPUTS)
    assert status == 0 and result['status'] == 'not_done' and 'binds no organization fact' in result['warnings'][0]
    assert not output.exists()


def test_an_output_that_cannot_be_written_is_a_warning(tmp_path, capsys):
    template = prior(tmp_path)
    blocked = tmp_path / 'file'
    blocked.write_text('x')
    status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(blocked / 'out.json'), *INPUTS)
    assert status == 0 and result['status'] == 'not_done' and 'cannot be written' in result['warnings'][0]


@pytest.mark.parametrize('arguments', [[], ['bogus'], ['journey'], ['journey', '--template', 'x'], ['aliases', '--unknown'], ['markers', '--bogus'], ['parent', '--bogus']])
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


TEMPLATES = [('runner-resolver-android', 'journey-driver.json'), ('runner-resolver-ios', 'journey-driver.json'),
             ('runner-resolver-ios', 'journey-execution.json'), ('runner-resolver-ios', 'image-build.json')]


@pytest.mark.parametrize('recipe, name', TEMPLATES)
def test_a_shipped_declaration_binds_no_organization_and_only_names_the_facts_to_bind(recipe, name):
    document = json.loads((RECIPES / recipe / name).read_text())
    bound = [fact for fact in tool.FACTS if fact in document and document[fact] is None]
    assert bound, (recipe, name)
    # Every fact field of a template is either null (bound at plan time) or a constant of the recipe.
    assert all(document[fact] is None or fact == 'driver' for fact in tool.FACTS if fact in document), (recipe, name)
    text = (RECIPES / recipe / name).read_text().lower()
    assert 'storefront' not in text and 'enviaflores' not in text and 'ef-' not in text


def test_no_recipe_file_carries_an_organization_binding_or_a_helper_default():
    """The values of an organization's journey, registry scope, host and credential variable are never in a recipe."""
    forbidden = ('enviaflores', 'ef-storefront', 'storefront', '@uxmaltech', 'npm.pkg.github.com', 'STOREFRONT_WEB_NPM_TOKEN')
    hits = []
    for path in RECIPES.rglob('*'):
        if (path.is_file() and path.suffix in {'.py', '.sh', '.json', '.md', ''} and '__pycache__' not in path.parts
                and path.name not in {'extraction.json', 'qa-extraction.json', 'test_plan_inputs.py'}
                and not path.name.startswith('test_')):
            text = path.read_text(errors='ignore')
            hits += [f'{path.relative_to(RECIPES)}: {word}' for word in forbidden if word in text]
    assert hits == []


def test_every_shipped_template_renders_with_example_facts_and_without_them_writes_nothing(tmp_path, capsys):
    for recipe, name in TEMPLATES:
        template = RECIPES / recipe / name
        output = tmp_path / recipe / name
        status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(output))
        assert status == 0 and result['status'] == 'not_done' and not output.exists(), (recipe, name)
        status, result, _ = render(capsys, 'journey', '--template', str(template), '--output', str(output), *INPUTS,
                                   *(['--driver', str(tmp_path / 'journey-driver.json')] if name == 'image-build.json' else []))
        assert status == 0 and result['status'] == 'rendered', (recipe, name)
        document = json.loads(output.read_text())
        assert document['profile'] == 'example-app-profile'
        assert set(json.loads(template.read_text())) == set(document)


def test_marker_aliases_are_written_to_the_image_owned_file(tmp_path, capsys):
    output = tmp_path / 'etc' / 'runner-android-emulator' / 'marker-aliases'
    status, result, err = render(capsys, 'markers', '--output', str(output), '--names', 'FORMER_OWNED NOT-A-NAME FORMER_OWNED OTHER_FORMER')
    assert status == 0 and result['status'] == 'ok' and result['names'] == ['FORMER_OWNED', 'OTHER_FORMER']
    assert len(result['warnings']) == 1 and "'NOT-A-NAME'" in err
    assert output.read_text() == 'FORMER_OWNED\nOTHER_FORMER\n'
    assert stat.S_IMODE(output.stat().st_mode) == 0o644


def test_marker_aliases_come_from_the_build_argument_and_none_writes_no_file(tmp_path, capsys):
    output = tmp_path / 'marker-aliases'
    status, result, _ = render(capsys, 'markers', '--output', str(output), environment={'RUNNER_ANDROID_MARKER_ALIASES': 'FROM_ENV'})
    assert result['status'] == 'ok' and output.read_text() == 'FROM_ENV\n'
    other = tmp_path / 'none'
    status, result, err = render(capsys, 'markers', '--output', str(other))
    assert status == 0 and result['status'] == 'none' and result['warnings'] == [] and not other.exists()
    assert err.startswith('NOTE: ')


def test_an_unwritable_marker_file_is_a_warning(tmp_path, capsys):
    blocked = tmp_path / 'file'
    blocked.write_text('x')
    status, result, _ = render(capsys, 'markers', '--output', str(blocked / 'marker-aliases'), '--names', 'FORMER_OWNED')
    assert status == 0 and result['status'] == 'not_done' and 'cannot be written' in result['warnings'][0]


def test_registry_bindings_are_written_with_the_variable_name_only(tmp_path, capsys):
    output = tmp_path / 'etc' / 'registries'
    spec = '@example-scope=packages.example.test=EXAMPLE_NPM_TOKEN @other=registry.example.test:8443/npm bad @x=host=1BAD @y=h=A=B'
    status, result, err = render(capsys, 'registries', '--output', str(output), '--entries', spec)
    assert status == 0 and result['status'] == 'ok'
    assert output.read_text() == '@example-scope=packages.example.test=EXAMPLE_NPM_TOKEN\n@other=registry.example.test:8443/npm\n'
    assert len(result['warnings']) == 3 and err.count('WARNING:') == 3
    assert 'EXAMPLE_NPM_TOKEN' not in ''.join(result['warnings'])


def test_no_registry_binding_writes_no_file(tmp_path, capsys):
    output = tmp_path / 'registries'
    status, result, err = render(capsys, 'registries', '--output', str(output))
    assert status == 0 and result['status'] == 'none' and not output.exists() and err.startswith('NOTE: ')


APPROVED = 'sha256:' + 'a' * 64
OTHER = 'sha256:' + 'b' * 64


def parent(capsys, *arguments, environment=None):
    return render(capsys, 'parent', *arguments, environment=environment)


def test_a_digest_qualified_parent_that_is_the_approved_artifact_is_verified(capsys):
    status, result, err = parent(capsys, '--reference', f'registry.example.test/example-android@{APPROVED}', '--approved', APPROVED)
    assert status == 0 and result['status'] == 'verified' and result['warnings'] == [] and err == ''


def test_a_resolved_digest_that_differs_from_the_approved_one_stops(capsys):
    status, result, _ = parent(capsys, '--reference', f'registry.example.test/example-android@{OTHER}', '--approved', APPROVED)
    assert status == 1 and result['status'] == 'mismatch'
    assert 'another artifact' in result['warnings'][-1] and OTHER in result['warnings'][-1]


@pytest.mark.parametrize('arguments', [
    # A tag is mutable: whatever digest it resolved to when it was observed, the build pulls the tag again.
    ['--reference', 'example-android:local', '--approved', APPROVED, '--resolved', APPROVED],
    ['--reference', 'example-android:local', '--approved', APPROVED, '--resolved', OTHER],
    ['--reference', 'example-android:local', '--approved', APPROVED],
    ['--reference', 'example-android:local', '--resolved', APPROVED],
    ['--reference', 'example-android:local'],
    ['--reference', 'example-android'],
])
def test_a_parent_named_by_a_mutable_tag_stops_whatever_else_was_given(capsys, arguments):
    """`main` rejects a parent that is not digest-qualified; the identity of the bytes built from is integrity."""
    status, result, err = parent(capsys, *arguments)
    assert status == 1 and result['status'] == 'mutable' and err.startswith('WARNING: ')
    assert any('mutable' in warning and '<image>@sha256:<digest>' in warning for warning in result['warnings'])


@pytest.mark.parametrize('arguments, expected', [
    (['--reference', f'example-android@{APPROVED}'], 'no approved digest'),
    (['--reference', f'example-android@{APPROVED}', '--approved', 'not-a-digest'], 'is not sha256:<64 hex>'),
    (['--reference', f'example-android@{APPROVED}', '--approved', APPROVED, '--resolved', 'not-a-digest'], 'is not sha256:<64 hex>'),
])
def test_a_digest_qualified_parent_that_cannot_be_approved_warns_and_the_build_goes_on(capsys, arguments, expected):
    status, result, _ = parent(capsys, *arguments)
    assert status == 0 and result['status'] in {'unverified', 'verified'}
    assert any(expected in warning for warning in result['warnings'])


def test_no_parent_reference_is_unverified_and_the_build_goes_on(capsys):
    status, result, _ = parent(capsys, '--reference', '')
    assert status == 0 and result['status'] == 'unverified'
    assert any('no parent reference' in warning for warning in result['warnings'])


def test_the_parent_check_reads_the_build_arguments_from_the_environment(capsys):
    environment = {'RUNNER_PARENT_REFERENCE': f'example-android@{OTHER}', 'RUNNER_PARENT_DIGEST': APPROVED}
    status, result, _ = parent(capsys, environment=environment)
    assert status == 1 and result['status'] == 'mismatch'
    environment = {'RUNNER_PARENT_REFERENCE': 'example-android:local', 'RUNNER_PARENT_DIGEST': APPROVED}
    status, result, _ = parent(capsys, environment=environment)
    assert status == 1 and result['status'] == 'mutable'


GUARDED = {
    'recipes/android', 'recipes/collab-runners/runner-agent-base', 'recipes/collab-runners/runner-base',
    'recipes/collab-runners/runner-ci-ai-resources', 'recipes/collab-runners/runner-ci-airflow-dag',
    'recipes/collab-runners/runner-ci-php-laravel', 'recipes/collab-runners/runner-ci-web-e2e',
    'recipes/templates/runner-base', 'recipes/templates/agent-base/flavors'}
REFERENCE_GUARD = re.compile(r'case "\$\{([A-Za-z_]+)\}" in (\*@sha256:\*[^)]*)\) ;;(.*?)esac')


def sh_guard(block, variable, value):
    """Runs one Dockerfile guard (`case ... esac`, then a success marker) with the reference set to `value`."""
    import subprocess
    result = subprocess.run(['sh', '-c', f'{block} && echo passed'], env={variable: value, 'PATH': os.environ['PATH']},
                            capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_every_dockerfile_that_main_guards_still_stops_on_a_reference_that_is_not_digest_qualified():
    """A tag is mutable: building from it is not building from the approved bytes. Spelling is not the issue, identity is."""
    root = RECIPES.parents[1]
    found = set()
    for dockerfile in sorted((root / 'recipes').rglob('*Dockerfile')):
        text = dockerfile.read_text().replace('\\\n', ' ')
        for match in REFERENCE_GUARD.finditer(text):
            variable, block = match.group(1), match.group(0)
            found.add(dockerfile.parent.relative_to(root).as_posix())
            digest = 'registry.example.test/example-image@sha256:' + 'a' * 64
            code, out, _ = sh_guard(block, variable, digest)
            assert (code, out.strip()) == (0, 'passed'), (dockerfile, variable)
            for tag in ('registry.example.test/example-image:latest', 'registry.example.test/example-image'):
                code, out, err = sh_guard(block, variable, tag)
                assert code != 0 and 'passed' not in out and err.strip(), (dockerfile, variable, tag)
    assert found == GUARDED


def test_the_android_resolver_reaches_the_digest_check_through_its_build_arguments():
    text = (RECIPES / 'runner-resolver-android' / 'Dockerfile').read_text()
    assert 'plan-inputs.py parent' in text and 'ARG RUNNER_ANDROID_IMAGE_DIGEST=' in text
    assert 'ARG RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST=' in text
    assert 'ENV RUNNER_ANDROID_EMULATOR_OWNED_ALIASES' not in text


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
    driver = {'schema_version': 1, 'repository': None, 'profile': None, 'backend': 'linux-docker',
              'driver': 'android-maestro', 'validator': None, 'maximum_seconds': 7200}
    android = tmp_path / 'android.json'
    render(capsys, 'journey', '--template', str(prior(tmp_path, driver, 'android-template.json')), '--output', str(android), *INPUTS)
    monkeypatch.setattr(docker_journey, 'DRIVER', android)
    docker_journey.validate_recipe()  # raises when the image driver differs from the pack's declaration

    ios_driver = {**driver, 'backend': 'macos-tart', 'driver': 'ios-maestro'}
    ios = tmp_path / 'ios.json'
    render(capsys, 'journey', '--template', str(prior(tmp_path, ios_driver, 'ios-template.json')), '--output', str(ios), *INPUTS)
    journey_jobs.driver(json.loads(ios.read_text()))

    execution = {'schema_version': 2, 'repository': None, 'profile': None, 'pack_root': '/opt/collab/repo-pack',
                 'python': '/opt/collab/runtime/bin/python3.12', 'driver': '/opt/ai-repo-resources/journey-driver.json',
                 'runtime_root': '/opt/collab/runtime', 'capability': 'repo.journey.ios.v2'}
    rendered = tmp_path / 'execution.json'
    render(capsys, 'journey', '--template', str(prior(tmp_path, execution, 'execution-template.json')), '--output', str(rendered), *INPUTS)
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


def test_the_shipped_templates_rendered_with_the_packs_values_pass_the_pinned_runtime(tmp_path, monkeypatch, capsys):
    """The shipped templates, filled with the facts a pack declares, are what the pinned runtime accepts."""
    docker_journey, journey_jobs, native_image = pinned_runtime(tmp_path, monkeypatch)
    android = tmp_path / 'journey-driver.json'
    render(capsys, 'journey', '--template', str(RECIPES / 'runner-resolver-android' / 'journey-driver.json'),
           '--output', str(android), *INPUTS)
    monkeypatch.setattr(docker_journey, 'DRIVER', android)
    docker_journey.validate_recipe()

    ios = tmp_path / 'ios-driver.json'
    render(capsys, 'journey', '--template', str(RECIPES / 'runner-resolver-ios' / 'journey-driver.json'),
           '--output', str(ios), *INPUTS)
    journey_jobs.driver(json.loads(ios.read_text()))
    execution = tmp_path / 'execution.json'
    render(capsys, 'journey', '--template', str(RECIPES / 'runner-resolver-ios' / 'journey-execution.json'),
           '--output', str(execution), *INPUTS)
    declared = native_image.execution_declaration(json.loads(execution.read_text()))
    assert declared['repository'] == 'example-org/example-app'
    assert declared['driver'] == '/opt/ai-repo-resources/journey-driver.json'


def test_a_template_left_unrendered_is_a_missing_binding_not_another_organizations(tmp_path, monkeypatch, capsys):
    """Without inputs no binding exists in the image, so the runtime has nothing of a different organization to mismatch."""
    docker_journey, journey_jobs, native_image = pinned_runtime(tmp_path, monkeypatch)
    output = tmp_path / 'journey-driver.json'
    render(capsys, 'journey', '--template', str(RECIPES / 'runner-resolver-android' / 'journey-driver.json'), '--output', str(output))
    assert not output.exists()
    monkeypatch.setattr(docker_journey, 'DRIVER', output)
    with pytest.raises(Exception):
        docker_journey.validate_recipe()
