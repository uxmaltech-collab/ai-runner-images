"""Configure the canonical disposable session from its policy and verified payload."""
import hashlib
import json
from pathlib import Path
import sys
import time


def configure(root, commit, image, resources, paths):
    policy = json.loads((root / 'native-tools-policy.json').read_text())
    modules = json.loads((root / 'MODULES.json').read_text())
    swiftlint = json.loads((root / 'swiftlint/pins.json').read_text())
    runner = policy['session_policy']['runner']
    tools = {
        'swiftlint': ('/opt/ai-runner-images/bin/swiftlint', ['version'], swiftlint['version']),
        'python': (paths['python'], ['--version'], policy['python']['version_contains']),
    }
    config = {
        'schema_version': 1, 'qualification_only': True, 'image_export_permitted': False,
        'repository': policy['repository'], 'recipe_commit': commit,
        'session_source_commit': modules['source_commit'], 'image': image,
        'deadline_unix': int(time.time()) + policy['deadline_seconds'], 'resources': resources,
        'guest_user': runner['name'], 'guest_home': runner['home'],
        'session_policy': policy['session_policy'],
        'environment': {'PATH': ':'.join(part.format(**paths) for part in policy['path']),
                        'DEVELOPER_DIR': paths['developer_dir'], 'JAVA_HOME': paths['java_home']},
        'tools': {name: {'path': path, 'sha256': hashlib.sha256(Path(path).resolve().read_bytes()).hexdigest(),
                        'version_args': args, 'version_contains': version}
                  for name, (path, args, version) in tools.items()},
    }
    (root / 'qualification-session.py').chmod(0o755)
    target = root / 'qualification.json'
    with target.open('x') as stream:
        json.dump(config, stream, indent=2)
        stream.write('\n')
    target.chmod(0o644)
    commands = root / 'commands'
    commands.mkdir(mode=0o755)
    commands.chmod(0o755)
    command = {'tool': 'python', 'args': ['-I', '-B', str(root / 'swiftlint/qualify.py'),
               '--output', runner['home'] + '/swiftlint-qualification'], 'cwd': runner['home']}
    target = commands / 'swiftlint.json'
    with target.open('x') as stream:
        json.dump(command, stream)
        stream.write('\n')
    target.chmod(0o644)
    return {'configuration_sha256': hashlib.sha256((root / 'qualification.json').read_bytes()).hexdigest(),
            'tools': config['tools']}


if __name__ == '__main__':
    paths = json.loads(Path('/opt/ai-runner-images/toolchain-paths.json').read_text())
    Path('/private/var/lib/ai-runner-qualification').mkdir(mode=0o700)
    print(json.dumps(configure(Path(__file__).resolve().parent, sys.argv[1], sys.argv[2],
                               json.loads(sys.argv[3]), paths)))
