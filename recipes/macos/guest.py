#!/usr/bin/env python3
"""Invoke existing tool recipes inside the owned accountless composition guest."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from recipes.macos.budgets import install_budget


def installer(recipe):
    spec = importlib.util.spec_from_file_location('native_tool_installer', recipe / 'install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(path, pin, mode=None):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError(f'Unprotected tool: {path}')
    if info.st_size != pin['bytes'] or sha(path) != pin['sha256']:
        raise ValueError(f'Tool differs from the locked bytes: {path}')
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f'Tool permissions differ: {path}')
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or info.st_mode & 0o005 != 0o005:
            raise ValueError(f'Runner cannot traverse protected tool parent: {parent}')
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--profile', choices=['macos-ios', 'macos-flutter'], required=True)
    parser.add_argument('--parent-layer', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    if os.getuid() != 0 or sys.platform != 'darwin':
        raise ValueError('The composition requires root inside a macOS guest')
    if not subprocess.check_output(['/usr/sbin/sysctl', '-n', 'hw.model'], text=True).startswith('VirtualMac'):
        raise ValueError('A virtual builder is required')
    users = subprocess.check_output(['/usr/bin/dscl', '.', '-list', '/Users', 'UniqueID'], text=True)
    if any(int(row.split()[-1]) >= 500 for row in users.splitlines()) or Path('/private/etc/kcpassword').exists():
        raise ValueError('Reusable images must remain accountless')
    root = args.root
    evidence = root / 'evidence'
    evidence.mkdir(mode=0o700)
    result = {'recipe_commit': args.commit, 'profile': args.profile, 'commands': [], 'components': {},
              'accounts_created': 0, 'credentials_received': False, 'runtime_admission': False}
    budgets = install_budget(args.profile, args.parent_layer)['component_seconds']
    def run(label, command):
        with (evidence / (label + '.stdout')).open('xb') as out, (evidence / (label + '.stderr')).open('xb') as err:
            process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=budgets[label])
        result['commands'].append({'name': label, 'argv': command, 'exit_code': process.returncode})
        if process.returncode:
            raise RuntimeError(f'Recipe {label} failed; original guest evidence is preserved')
    # Require the neutral base's existing tool declaration. No Xcode reinstall or probe suite.
    base = Path('/opt/ai-runner-images/base-receipt.json')
    prior = json.loads(base.read_text())
    preserved = {}
    for name, expected in prior['preserved_executables'].items():
        # The native RPC is an external owner; its later canonical replacement is
        # retained, not copied or overwritten by this tool recipe.
        if name.endswith('/tart-guest-agent'):
            continue
        path = Path(name)
        if sha(path) != expected:
            raise ValueError(f'Inherited base tool changed: {name}')
        preserved[name] = expected
    result['inherited_base'] = {'receipt_sha256': sha(base), 'executables': preserved,
                                'version_and_simulator_evidence': 'reused-from-physical-parent'}
    recipes = root / 'recipes'
    artifacts = root / 'artifacts'
    # SwiftLint belongs to the native tool layer; all engines remain together above it.
    swiftlint = recipes / 'macos-xcode-maestro/swiftlint'
    pins = json.loads((swiftlint / 'pins.json').read_text())
    swift_recipe = installer(swiftlint)
    swiftroot, swiftbin = swift_recipe.layout('neutral', pins)
    if not swiftroot.exists():
        run('swiftlint', [sys.executable, '-I', '-B', str(swiftlint / 'install.py'),
            '--archive', str(artifacts / 'portable_swiftlint.zip'), '--receipt', str(evidence / 'swiftlint.json')])
        action = 'installed'
    else:
        action = 'reused-verified'
    files = [checked(swiftroot / name, pin, int(pin['mode'], 8)) for name, pin in pins['members'].items()]
    launcher = swiftbin / 'swiftlint'
    expected = swift_recipe.launcher_bytes(swiftroot)
    checked(launcher, {'bytes': len(expected), 'sha256': hashlib.sha256(expected).hexdigest()}, 0o755)
    result['components']['swiftlint'] = {'action': action, 'version': pins['version'], 'files': files,
                                       'launcher_sha256': sha(launcher), 'runtime_path': str(launcher.parent)}
    agents = recipes / 'agent-build'
    pins = json.loads((agents / 'pins.json').read_text())
    agent_recipe = installer(agents)
    agentroot = agent_recipe.PREFIX
    if args.parent_layer == 'macos-xcode-maestro':
        run('agents', [sys.executable, '-I', '-B', str(agents / 'install.py'), '--artifacts', str(artifacts),
            '--codex-binary', str(artifacts / pins['codex']['binary']['installed_name']), '--codex-companion', str(artifacts / pins['codex']['companion']['installed_name']),
            '--receipt', str(evidence / 'agents.json')])
        action = 'installed'
    else:
        action = 'reused-verified'
    if (agentroot / 'pins.json').read_bytes() != (agents / 'pins.json').read_bytes():
        raise ValueError('Inherited agent lock differs from the recipe')
    files = [checked(agentroot / path, pin, 0o755) for path, pin in [
        ('codex/codex', pins['codex']['binary']), ('codex/codex-code-mode-host', pins['codex']['companion']),
        ('claude/claude', pins['claude']), ('grok/grok', pins['grok'])]]
    for engine in pins['engines']:
        wrapper = agent_recipe.launcher_bytes(engine)
        checked(agentroot / 'bin' / engine, {'bytes': len(wrapper),
                'sha256': hashlib.sha256(wrapper).hexdigest()}, 0o755)
    result['components']['agents'] = {'action': action, 'engines': pins['engines'], 'files': files}
    if args.profile == 'macos-flutter':
        flutter = recipes / 'flutter-dart'
        if args.parent_layer != 'flutter-dart-ios':
            run('flutter', [sys.executable, '-I', '-B', str(flutter / 'install.py'), '--archive',
                str(artifacts / 'flutter.zip'), '--evidence-dir', str(evidence / 'flutter'),
                '--runtime-python', sys.executable])
            action = 'installed'
        else:
            action = 'reused-verified'
        pins = json.loads((flutter / 'pins.json').read_text())
        sdk = Path('/opt/ai-runner-images/flutter')
        if (sdk / 'pins.json').read_bytes() != (flutter / 'pins.json').read_bytes():
            raise ValueError('Inherited Flutter lock differs from the recipe')
        ready = json.loads((sdk / pins['flutter_version'] / 'SDK-READY.json').read_text())
        if ready['manifest_sha256'] != sha(sdk / pins['flutter_version'] / 'SDK-MANIFEST.json'):
            raise ValueError('Inherited Flutter manifest differs from its ready receipt')
        if ready['flutter_revision'] != pins['flutter_revision'] or ready['dart_version'] != pins['dart_version']:
            raise ValueError('Inherited Flutter versions differ')
        if (sdk / 'launcher.py').read_bytes() != (flutter / 'launcher.py').read_bytes():
            raise ValueError('Inherited Flutter launcher differs from the recipe')
        result['components']['flutter'] = {'action': action, 'ready': ready,
            'reused_evidence_scope': 'unchanged SDK and precache bound by the physical parent tuple'}
    result['runtime_path'] = ':'.join((['/opt/ai-runner-images/flutter/bin'] if args.profile == 'macos-flutter' else []) +
        ['/opt/ai-runner-images/agents/bin', '/opt/ai-runner-images/bin', '/usr/bin', '/bin', '/usr/sbin', '/sbin'])
    (evidence / 'COMPONENTS.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
