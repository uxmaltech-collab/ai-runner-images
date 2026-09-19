#!/usr/bin/env python3
"""Build local runner images from canonical recipes with one entrypoint.

The input document selects declared inputs, never arbitrary host commands.
Image building does not admit an image, deploy a service or register a runner.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    'android': ('Linux', 'recipes/android/build.py'),
    'linux-control-plane': ('Linux', 'stacks/linux-control-plane/pipeline.py'),
    'macos-ios': ('Darwin', 'recipes/macos/build.py'),
    'macos-flutter': ('Darwin', 'recipes/macos/build.py'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['plan', 'build'])
    parser.add_argument('--profile', required=True, choices=PROFILES)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--work-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    started = False
    try:
        raw = args.inputs.read_bytes()
        document = json.loads(raw)
        if not isinstance(document, dict) or document.get('schema_version') != 1 or document.get('profile') != args.profile:
            raise ValueError('Input schema/profile mismatch')
        if set(document) != {'schema_version', 'profile', 'inputs'} or not isinstance(document['inputs'], dict):
            raise ValueError('Expected schema_version, profile and inputs')
        system, relative = PROFILES[args.profile]
        source = ROOT / relative
        commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain']))
        plan = {'schema_version': 1, 'profile': args.profile, 'source_commit': commit,
                'source_clean': not dirty,
                'inputs_sha256': hashlib.sha256(raw).hexdigest(), 'backend': relative,
                'platform': system, 'backend_available': source.is_file(),
                'work_dir': str(args.work_dir.resolve()), 'runtime_admission': False}
        if args.operation == 'plan':
            print(json.dumps(plan, indent=2))
            return 0 if source.is_file() else 2
        if platform.system() != system:
            raise ValueError(f'{args.profile} must run on {system}')
        if not source.is_file():
            raise ValueError(f'Native backend not promoted yet: {relative}')
        if dirty:
            raise ValueError('Commit recipe changes before building; use a clean source checkout')
        args.work_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
        started = True
        (args.work_dir / 'PLAN.json').write_text(json.dumps(plan, indent=2) + '\n')
        spec = importlib.util.spec_from_file_location('image_build_backend', source)
        backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend)
        result = backend.build(document['inputs'], args.work_dir.resolve(), ROOT, commit,
                               profile=args.profile)
        (args.work_dir / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 0 if result.get('status') == 'passed' else 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result = {'status': 'failed', 'reason': str(error)}
        if started:
            (args.work_dir / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
