"""End-to-end entrypoint backend for the existing portable Linux stack."""
import subprocess
import sys


def build(inputs, work, root, commit, *, profile):
    if set(inputs) != {'templates_checkout'}:
        raise ValueError('linux-control-plane inputs require only templates_checkout')
    here = root / 'stacks/linux-control-plane'
    pack = work / 'pack'
    subprocess.run([sys.executable, str(here / 'materialize.py'), '--templates',
                    inputs['templates_checkout'], '--declaration', str(here / 'qualification.json'),
                    '--output', str(pack)], check=True)
    subprocess.run([sys.executable, str(here / 'build.py'), '--pack', str(pack),
                    '--evidence', str(work / 'build'), '--download-wheels'], check=True)
    subprocess.run([sys.executable, str(here / 'restore-rehearsal.py'),
                    '--build-receipt', str(work / 'build/BUILD.json'),
                    '--declaration', str(pack / 'declaration.json'),
                    '--evidence', str(work / 'restore')], check=True)
    return {'schema_version': 1, 'status': 'passed', 'profile': profile,
            'source_commit': commit, 'build': 'build/BUILD.json', 'restore': 'restore/RESTORE.json',
            'distribution': 'local-only', 'runtime_admission': False}
