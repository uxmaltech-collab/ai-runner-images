"""Neutral console relocation preserves source and can execute the relocated result."""
import base64, csv, hashlib, importlib.util, json, os, stat, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
import pytest

spec = importlib.util.spec_from_file_location('console_recipe', Path(__file__).with_name('relocate_console.py'))
recipe_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(recipe_module)

class RecipeAdapter:
    destination = None
    installer = None
    def main(self, args):
        runtime = Path(args[args.index('--runtime-tree') + 1])
        output = Path(args[args.index('--output-dir') + 1])
        try:
            if output.resolve().is_relative_to(runtime.resolve()):
                raise ValueError('recursive output')
            output.mkdir(mode=0o700, exist_ok=False)
            prepared, receipt = recipe_module.prepare_runtime(runtime, output / 'runtime', self.installer,
                canonical_path=lambda path: Path(path).resolve(strict=True),
                python_destination=self.destination, console_name='sample-cli',
                distribution_name='sample_cli', entrypoint='sample_cli.cli:main', python_version='3.12')
            (output / 'runtime-preparation.json').write_text(json.dumps(receipt))
            (output / 'image-manifest.json').write_text(json.dumps({'payloads':[
                {'source':str(prepared),'sha256':self.installer.tree_hash(prepared)}]}))
            return 0
        except (OSError, ValueError):
            return 2
image = RecipeAdapter()

INSTALLER = '''from pathlib import Path
import hashlib, json, stat
def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def tree_hash(root):
    root = Path(root)
    entries = []
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        entries.append([str(path.relative_to(root)), stat.S_IMODE(info.st_mode),
                        file_hash(path) if path.is_file() else None])
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()
def check_inputs(manifest):
    for record in manifest['payloads']:
        if tree_hash(Path(record['source'])) != record['sha256']:
            raise ValueError('artifact-digest-mismatch')
'''


@pytest.fixture
def recipe(tmp_path, monkeypatch):
    pack = tmp_path / 'pack'; pack.mkdir()
    original = tmp_path / 'input-python'; (original / 'bin').mkdir(parents=True)
    (original / 'bin/python3.12').write_bytes(b'unchanged Python fixture')
    console = original / 'bin/sample-cli'
    body = b'import sys\nfrom sample_cli.cli import main\nif __name__ == "__main__":\n    sys.exit(main())\n'
    console.write_bytes(b'#!/missing-private-builder/python3.12\n' + body)
    console.chmod(0o755)
    site = original / 'lib/python3.12/site-packages'
    package = site / 'sample_cli'; package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    (package / 'cli.py').write_text('def main():\n    print("relocated CLI fixture")\n    return 0\n')
    metadata = site / 'sample_cli-0.0.0.dist-info'; metadata.mkdir()
    (metadata / 'entry_points.txt').write_text('[console_scripts]\nsample-cli = sample_cli.cli:main\n')
    record = metadata / 'RECORD'
    record.write_text('../../../bin/sample-cli,sha256=old-generated-console,1\nsample_cli-0.0.0.dist-info/RECORD,,\n')
    (original / 'dependency.bin').write_bytes(b'unchanged dependency fixture')
    # Use the existing test interpreter read-only; long temporary paths can
    # exceed the host kernel's shebang limit before the fixture reaches Python.
    guest = Path(sys.executable).parent.parent
    assert (guest / 'bin/python3.12').is_file()
    image.destination = guest
    image.installer = None
    installer_path = tmp_path / 'installer.py'
    installer_path.write_text(INSTALLER)
    installer_spec = importlib.util.spec_from_file_location('console_fixture_installer', installer_path)
    installer = importlib.util.module_from_spec(installer_spec); installer_spec.loader.exec_module(installer)
    image.installer = installer
    output = tmp_path / 'output'
    args = ['--templates-root', str(tmp_path), '--base-manifest', str(tmp_path / 'base'),
            '--runtime-tree', str(original), '--output-dir', str(output), '--pack-commit', 'b' * 40]
    return SimpleNamespace(original=original, console=console, body=body, record=record,
                           installer=installer, output=output, args=args, guest=guest)


def test_recipe_output_cli_executes_after_relocation(recipe):
    before = recipe.installer.tree_hash(recipe.original)
    assert image.main(recipe.args) == 0
    manifest = json.loads((recipe.output / 'image-manifest.json').read_bytes())
    prepared = Path(manifest['payloads'][0]['source'])
    result = subprocess.run([str(prepared / 'bin/sample-cli')], capture_output=True, text=True,
        timeout=10, env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1',
                        'PYTHONPATH': str(prepared / 'lib/python3.12/site-packages')})
    assert result.returncode == 0, result.stderr
    assert result.stdout == 'relocated CLI fixture\n'
    assert prepared != recipe.original
    assert recipe.installer.tree_hash(recipe.original) == before
    script = (prepared / 'bin/sample-cli').read_bytes()
    assert script.split(b'\n', 1)[1] == recipe.body
    assert stat.S_IMODE((prepared / 'bin/sample-cli').stat().st_mode) == 0o755
    assert (prepared / 'dependency.bin').read_bytes() == (recipe.original / 'dependency.bin').read_bytes()
    rows = list(csv.reader((prepared / recipe.record.relative_to(recipe.original)).read_text().splitlines()))
    expected = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(script).digest()).decode().rstrip('=')
    assert rows[0] == ['../../../bin/sample-cli', expected, str(len(script))]
    assert rows[1] == ['sample_cli-0.0.0.dist-info/RECORD', '', '']
    receipt = json.loads((recipe.output / 'runtime-preparation.json').read_bytes())
    assert receipt['source_sha256'] == before
    assert receipt['prepared_sha256'] == manifest['payloads'][0]['sha256']
    assert {entry['path'] for entry in receipt['changes']} == {
        'bin/sample-cli', str(recipe.record.relative_to(recipe.original))}
    recipe.installer.check_inputs(manifest)


def test_already_relocated_input_is_reused_without_copy(recipe):
    recipe.console.write_bytes(('#!' + str(recipe.guest / 'bin/python3.12') + '\n').encode() + recipe.body)
    recipe.record.write_text('sample_cli-0.0.0.dist-info/RECORD,,\n')
    before = recipe.installer.tree_hash(recipe.original)
    assert image.main(recipe.args) == 0
    manifest = json.loads((recipe.output / 'image-manifest.json').read_bytes())
    assert manifest['payloads'][0]['source'] == str(recipe.original)
    assert not (recipe.output / 'runtime').exists()
    assert recipe.installer.tree_hash(recipe.original) == before


def test_console_not_listed_in_wheel_record_keeps_original_metadata(recipe):
    recipe.record.write_text('sample_cli-0.0.0.dist-info/RECORD,,\n')
    original = recipe.record.read_bytes()
    assert image.main(recipe.args) == 0
    manifest = json.loads((recipe.output / 'image-manifest.json').read_bytes())
    prepared = Path(manifest['payloads'][0]['source'])
    assert (prepared / recipe.record.relative_to(recipe.original)).read_bytes() == original


def test_relocated_console_with_stale_record_repairs_only_metadata(recipe):
    recipe.console.write_bytes(('#!' + str(recipe.guest / 'bin/python3.12') + '\n').encode() + recipe.body)
    before = recipe.installer.tree_hash(recipe.original)
    assert image.main(recipe.args) == 0
    receipt = json.loads((recipe.output / 'runtime-preparation.json').read_bytes())
    assert [entry['path'] for entry in receipt['changes']] == [str(recipe.record.relative_to(recipe.original))]
    assert (recipe.output / 'runtime/bin/sample-cli').read_bytes() == recipe.console.read_bytes()
    assert recipe.installer.tree_hash(recipe.original) == before


@pytest.mark.parametrize('invalid', ['script', 'entrypoint', 'record'])
def test_invalid_console_inputs_preserve_original_and_failed_preparation(recipe, invalid):
    if invalid == 'script':
        recipe.console.write_bytes(b'#!/bin/sh\necho invalid\n')
    elif invalid == 'entrypoint':
        (recipe.record.parent / 'entry_points.txt').write_text('[console_scripts]\nsample-cli = unrelated:main\n')
    else:
        recipe.record.write_text('../../../bin/sample-cli,hash,1\n../../../bin/sample-cli,other,2\n')
    before = recipe.installer.tree_hash(recipe.original)
    assert image.main(recipe.args) == 2
    assert recipe.output.is_dir()
    assert not (recipe.output / 'image-manifest.json').exists()
    assert recipe.installer.tree_hash(recipe.original) == before


def test_existing_preparation_is_not_overwritten(recipe):
    recipe.output.mkdir(); (recipe.output / 'original').write_text('keep')
    before = recipe.installer.tree_hash(recipe.original)
    assert image.main(recipe.args) == 2
    assert (recipe.output / 'original').read_text() == 'keep'
    assert recipe.installer.tree_hash(recipe.original) == before


def test_preparation_inside_runtime_cannot_copy_itself(recipe):
    nested = recipe.original / 'recursive-output'
    args = list(recipe.args); args[args.index('--output-dir') + 1] = str(nested)
    before = recipe.installer.tree_hash(recipe.original)
    assert image.main(args) == 2
    assert not nested.exists()
    assert recipe.installer.tree_hash(recipe.original) == before
