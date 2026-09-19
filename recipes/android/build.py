"""Build the neutral Android recipe and restore it in an isolated local store."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(argv, log, **kwargs):
    log.with_suffix(log.suffix + '.command.json').write_text(json.dumps(argv, indent=2) + '\n')
    with log.open('x') as output:
        result = subprocess.run(argv, stdout=output, stderr=subprocess.STDOUT, **kwargs)
    if result.returncode:
        raise ValueError(f'Command exited {result.returncode}; original log: {log}')


def build(inputs, work, root, commit, *, profile):
    allowed = {'templates_checkout', 'parent_receipt', 'recipe_commit'}
    if set(inputs) - allowed or not inputs.get('templates_checkout'):
        raise ValueError('Android inputs: templates_checkout, optional parent_receipt and recipe_commit')
    recipe_commit = inputs.get('recipe_commit', commit)
    if not re.fullmatch('[0-9a-f]{40}', recipe_commit):
        raise ValueError('recipe_commit must be an exact Git commit')
    # Keep working-tree edits and customer files out of the build context.
    context = work / 'context'; context.mkdir()
    archive = work / 'recipe-source.tar'
    run(['git', '-C', str(root), 'archive', '--format=tar', '--output', str(archive),
         recipe_commit, 'recipes/android'], work / 'source.log')
    with tarfile.open(archive) as source:
        source.extractall(context, filter='data')
    if inputs.get('parent_receipt'):
        parent_path = Path(inputs['parent_receipt']).resolve()
    else:
        module = root / 'stacks/linux-control-plane/pipeline.py'
        spec = importlib.util.spec_from_file_location('parent_pipeline', module)
        parent_pipeline = importlib.util.module_from_spec(spec); spec.loader.exec_module(parent_pipeline)
        parent_work = work / 'parent'; parent_work.mkdir()
        parent_pipeline.build({'templates_checkout': inputs['templates_checkout']}, parent_work,
                              root, commit, profile='linux-control-plane')
        parent_path = parent_work / 'build/BUILD.json'
    receipt = json.loads(parent_path.read_text())
    source_lock = json.loads((root / 'stacks/linux-control-plane/lock.json').read_text())
    if receipt['templates_commit'] != source_lock['templates']['commit']:
        raise ValueError('Parent receipt does not match the canonical stack lock')
    parent = receipt['images']['runner-agent-base']
    observed = json.loads(subprocess.check_output(['docker', 'image', 'inspect', parent['tag']]))[0]
    if (parent['reference'] not in observed['RepoDigests'] or observed['Id'] != parent['id']
            or observed['RootFS']['Layers'] != parent['layers']):
        raise ValueError('Immutable parent no longer matches its build receipt')
    key = hashlib.sha256((recipe_commit + parent['reference']).encode()).hexdigest()[:16]
    tag = f'ai-runner-images/runner-android:{key}'
    argv = ['docker', 'buildx', 'build', '--load', '--provenance=false', '--platform', 'linux/amd64',
            '--tag', tag, '--file', 'recipes/android/Dockerfile',
            '--build-context', parent['reference'] + '=docker-image://' + parent['tag'],
            '--build-arg', 'RUNNER_AGENT_BASE_IMAGE=' + parent['reference'],
            '--build-arg', 'RUNNER_SOURCE_COMMIT=' + recipe_commit, '.']
    run(argv, work / 'build.log', cwd=context)
    info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag]))[0]
    references = [ref for ref in info['RepoDigests'] if ref.startswith(tag.split(':')[0] + '@')]
    if len(references) != 1:
        raise ValueError('Build must produce one immutable local image reference')
    image = {'reference': references[0], 'tag': tag, 'id': info['Id'],
             'layers': info['RootFS']['Layers'], 'architecture': info['Architecture']}
    local_archive = work / 'android-image.tar'
    run(['docker', 'image', 'save', '--output', str(local_archive), tag], work / 'save.log')
    result = {'schema_version': 1, 'profile': profile, 'source_commit': commit,
              'recipe_commit': recipe_commit, 'recipe_archive_sha256': sha(archive),
              'parent_receipt_sha256': sha(parent_path), 'parent': parent, 'image': image,
              'archive': {'file': local_archive.name, 'bytes': local_archive.stat().st_size,
                          'sha256': sha(local_archive)}, 'status': 'built',
              'distribution': 'local-only', 'runtime_admission': False}
    (work / 'BUILD.json').write_text(json.dumps(result, indent=2) + '\n')
    run([sys.executable, str(root / 'recipes/android/restore.py'), '--build-receipt',
         str(work / 'BUILD.json'), '--evidence', str(work / 'restore')], work / 'restore.log')
    result.update(status='passed', restore='restore/RESTORE.json')
    return result
