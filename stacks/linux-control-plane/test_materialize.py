"""Behavioral checks against the exact consumed engine, not fake Dockerfiles."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("portable_materialize", HERE / "materialize.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def templates():
    path = os.environ.get("TEMPLATES_CHECKOUT")
    if not path:
        pytest.skip("integration requires the exact pinned TEMPLATES_CHECKOUT")
    return Path(path)


@pytest.mark.parametrize("field,value", [
    ("organization", "bad/name"), ("repository", "other-org/project"),
    ("environment_prefix", "X;bad"), ("runner_group_id", True),
    ("image_namespace", "image;command"), ("profile_id", "resolver-unconfigured"),
])
def test_invalid_bindings_do_not_create_a_pack(tmp_path, field, value):
    data = json.loads((HERE / "qualification.json").read_text())
    data[field] = value
    config = tmp_path / "input.json"
    config.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        module.declaration(config)


def test_repeat_materialization_preserves_all_source_bytes(templates, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    for output in (first, second):
        module.materialize(templates, HERE / "qualification.json", output, HERE / "lock.json")
    assert (first / "MATERIALIZATION.json").read_bytes() == (second / "MATERIALIZATION.json").read_bytes()
    lock = json.loads((HERE / "lock.json").read_text())
    for path in lock["templates"]["files"]:
        original = subprocess.check_output(["git", "-C", str(templates), "show",
            f"{lock['templates']['commit']}:{path}"])
        actual = (first / path).read_bytes()
        if path.endswith(("/profile.py", "/policy.py")):
            assert module.core(original) == module.core(actual)
        else:
            assert original == actual
    with pytest.raises(ValueError, match="new directory"):
        module.materialize(templates, HERE / "qualification.json", first, HERE / "lock.json")


def test_bad_source_digest_does_not_emit_a_partial_pack(templates, tmp_path):
    lock = json.loads((HERE / "lock.json").read_text())
    lock["templates"]["files"]["runners/control-plane/app.py"] = "0" * 64
    path = tmp_path / "bad-lock.json"
    path.write_text(json.dumps(lock))
    output = tmp_path / "result"
    with pytest.raises(ValueError, match="source digest mismatch"):
        module.materialize(templates, HERE / "qualification.json", output, path)
    assert not output.exists()


@pytest.mark.parametrize("organization,prefix", [("collab-e2e-org", "COLLAB_E2E"), ("another-tenant", "ANOTHER")])
def test_real_engine_routes_declared_tenant_and_rejects_foreign_repository(templates, tmp_path, organization, prefix):
    data = json.loads((HERE / "qualification.json").read_text())
    data.update(organization=organization, repository=organization + "/collab-delivery", environment_prefix=prefix)
    config = tmp_path / "declaration.json"
    config.write_text(json.dumps(data))
    output = tmp_path / "pack"
    module.materialize(templates, config, output, HERE / "lock.json")
    program = '''
import sys
from pathlib import Path
from runner_control_plane import load_catalog, RunnerRouter, AuthorizationError
from runner_control_plane.policy import policy_for
from runner_control_plane.spawner import build_run_argv
catalog = load_catalog(Path(sys.argv[1]) / 'runners/catalog.yaml')
router = RunnerRouter(catalog, 'github-runners-host-sre')
profile = catalog.profiles[0]
spec = router.build_spawn_spec(repository=sys.argv[2], labels=profile.labels,
    environment={profile.image_digest_env: 'sha256:' + 'a'*64})
argv = build_run_argv(spec, policy_for(profile.id), '123')
assert spec.repository == sys.argv[2]
assert argv[argv.index('--pull') + 1] == 'never'
assert 'docker.sock' not in ' '.join(argv)
assert 'github-app' not in ' '.join(argv)
assert sys.argv[3] + '_JIT_CONFIG' in argv
try:
    router.build_spawn_spec(repository='foreign-org/project', labels=profile.labels,
        environment={profile.image_digest_env: 'sha256:' + 'a'*64})
except AuthorizationError:
    pass
else:
    raise AssertionError('foreign repository accepted')
'''
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": str(output / "runners/control-plane"),
           prefix + "_IMAGE_PULL_POLICY": "never"}
    subprocess.run([sys.executable, "-c", program, str(output), data["repository"], prefix], env=env, check=True)
