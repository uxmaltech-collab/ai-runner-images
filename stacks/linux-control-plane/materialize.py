#!/usr/bin/env python3
"""Create a complete CI pack from an exact template commit and tenant declaration.

No credentials, GitHub writes, Docker operations or local checkout contents are
used. Shared source bytes outside the two documented profile blocks stay exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def declaration(path: Path) -> dict:
    data = json.loads(path.read_text())
    expected = {
        "schema_version", "organization", "repository", "environment_prefix",
        "workload", "sentinel", "label_namespace", "image_namespace",
        "egress_network", "runner_group_id", "profile_id",
    }
    if set(data) != expected or data["schema_version"] != 1:
        raise ValueError("unsupported declaration fields or schema")
    patterns = {
        "organization": r"[A-Za-z0-9][A-Za-z0-9-]{0,38}",
        "repository": r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+",
        "environment_prefix": r"[A-Z][A-Z0-9_]+",
        "workload": r"[a-z][a-z0-9-]{1,62}",
        "sentinel": r"[a-z][a-z0-9-]{1,62}",
        "label_namespace": r"[a-z][a-z0-9.-]+",
        "image_namespace": r"[a-z0-9][a-z0-9._/-]*",
        "egress_network": r"[a-z][a-z0-9-]{1,62}",
        "profile_id": r"ci-[a-z0-9-]+",
    }
    for key, pattern in patterns.items():
        if not isinstance(data[key], str) or not re.fullmatch(pattern, data[key]):
            raise ValueError(f"invalid {key}")
    if data["repository"].split("/")[0] != data["organization"]:
        raise ValueError("repository must belong to declared organization")
    if type(data["runner_group_id"]) is not int or data["runner_group_id"] < 1:
        raise ValueError("runner_group_id must be positive")
    return data


def replace_profile(raw: bytes, assignments: str) -> bytes:
    text = raw.decode()
    # Marker lines belong to the shared core; only their interior is replaced.
    pattern = r"(?m)(^# >>> pack-profile[^\n]*\n).*?(^# <<< pack-profile[^\n]*$)"
    matches = list(re.finditer(pattern, text, flags=re.S))
    if len(matches) != 1:
        raise ValueError("expected exactly one pack-profile block")
    return re.sub(pattern, lambda m: m[1] + assignments + "\n" + m[2], text, flags=re.S).encode()


def core(raw: bytes) -> bytes:
    return replace_profile(raw, "<profile>")


def materialize(templates: Path, config: Path, output: Path, lock_path: Path) -> dict:
    config_data = declaration(config)
    lock = json.loads(lock_path.read_text())
    revision = lock["templates"]["commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("template commit must be an exact SHA")
    if output.exists():
        raise ValueError("output must be a new directory")
    source = {}
    for path, expected in lock["templates"]["files"].items():
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("invalid locked source path")
        raw = subprocess.check_output(["git", "-C", str(templates), "show", f"{revision}:{path}"])
        if digest(raw) != expected:
            raise ValueError(f"source digest mismatch: {path}")
        source[path] = raw
    d = config_data
    prefix, profile_id = d["environment_prefix"], d["profile_id"]
    profile = {
        "ENV_PREFIX": prefix, "ORGANIZATION": d["organization"],
        "REPOSITORY": d["repository"], "WORKLOAD": d["workload"],
        "RUNNER_SENTINEL": d["sentinel"], "LABEL_NAMESPACE": d["label_namespace"],
        "IMAGE_PREFIX": d["image_namespace"] + "/",
        "DEFAULT_SOURCE_HOST_PATH": "/opt/runner-pack/source",
        "DEFAULT_SOURCE_CONTAINER_PATH": "/actions-runner/_work/source",
        "DEFAULT_SOT_MIRROR_HOST_PATH": "/opt/runner-pack/mirror",
        "DEFAULT_STATE_ROOT": "/var/lib/runner-control-plane",
        "DEFAULT_RUNNER_WORK_HOST_ROOT": "/opt/runner-pack/work",
    }
    profile_text = "\n".join(f"{key} = {value!r}" for key, value in profile.items())
    profile_text += f"\nEXPECTED_PROFILE_IDS = frozenset({[profile_id]!r})"
    profile_text += "\nALLOWED_SHARED_IMAGES = frozenset()\nRESOLVER_ENGINE_OVERRIDES = {}"
    policy_text = (
        f"EGRESS_GITHUB = {d['egress_network']!r}\n"
        f"DEFAULT_RUNNER_GROUP_ID = {d['runner_group_id']}\n"
        f"POLICY_KWARGS = {{{profile_id!r}: {{'cpus': 1, 'mem_gib': 2, "
        "'max_concurrent': 1, 'job_timeout_min': 10}}"
    )
    transformed = dict(source)
    for filename, text in (("profile.py", profile_text), ("policy.py", policy_text)):
        key = "runners/control-plane/runner_control_plane/" + filename
        transformed[key] = replace_profile(source[key], text)
        if core(transformed[key]) != core(source[key]):
            raise ValueError("profile replacement changed shared core")
    output.mkdir(parents=True)

    def write(path: str, data: bytes):
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    for path, data in transformed.items():
        write(path, data)
    leaf = "runner-" + profile_id
    item = {
        "id": profile_id, "mode": "ephemeral",
        "labels": ["self-hosted", d["sentinel"], profile_id],
        "repository": d["repository"], "image": d["image_namespace"] + "/" + leaf,
        "dockerfile": "runners/images/" + leaf + "/Dockerfile",
        "image_digest_env": prefix + "_CI_IMAGE_DIGEST",
        "manifest": f"runners/manifests/{profile_id}.yaml",
    }
    catalog = {
        "schema_version": 2, "sentinel": d["sentinel"],
        "control_plane": {
            "publisher": "github-runners-host-sre", "singleton": True,
            "source_branch": "main", "image": d["image_namespace"] + "/runner-control-plane",
            "dockerfile": "runners/control-plane/Dockerfile",
            "image_digest_env": prefix + "_CONTROL_PLANE_IMAGE_DIGEST",
        }, "runners": [item],
    }
    # JSON is a YAML subset; deterministic serialization avoids a renderer dependency.
    write("runners/catalog.yaml", encoded(catalog))
    manifest = {k: v for k, v in item.items() if k != "manifest"}
    manifest.update(schema_version=2, lineage=["runner-base", leaf])
    write(item["manifest"], encoded(manifest))
    write(item["dockerfile"], b"ARG RUNNER_BASE_IMAGE\nFROM ${RUNNER_BASE_IMAGE}\nUSER runner\n")
    write("runners/control-plane/Dockerfile", (HERE / "control-plane.Dockerfile").read_bytes())
    write("entrypoint.py", (HERE / "entrypoint.py").read_bytes())
    write("requirements.lock", (HERE / "requirements.lock").read_bytes())
    write("wheels.lock.json", (HERE / "wheels.lock.json").read_bytes())
    write(".dockerignore", b"**/__pycache__\n**/*.pyc\n.git\ncredentials\n*.pem\n*.env\n")
    write("declaration.json", encoded(d))
    write("source-lock.json", encoded(lock))
    workflow = f'''name: Runner portability canary
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  qualify:
    timeout-minutes: 10
    runs-on: [self-hosted, {d['sentinel']}, {profile_id}]
    steps:
      - name: Verify execution and image contract
        shell: bash
        env:
          EXPECTED_REPOSITORY: {d['repository']}
        run: |
          set -euo pipefail
          test "$GITHUB_REPOSITORY" = "$EXPECTED_REPOSITORY"
          test "$(id -u)" = 1001
          test -n "${{{prefix}_CI_IMAGE_DIGEST}}"
          test ! -S /var/run/docker.sock
          test ! -e /run/secrets/github-app.pem
          git --version
          gh --version
          actionlint --version
          docker --version
          python3 -c 'import hashlib; assert hashlib.sha256(b"portable").hexdigest() == "{digest(b'portable')}"'
          printf 'repository=%s\\nimage=%s\\n' "$GITHUB_REPOSITORY" "${{{prefix}_CI_IMAGE_DIGEST}}" >> "$GITHUB_STEP_SUMMARY"
'''
    write(".github/workflows/runner-portability.yml", workflow.encode())
    compose = {
        "name": d["workload"],
        "services": {"control-plane": {
            "image": d["image_namespace"] + "/runner-control-plane@${CONTROL_PLANE_DIGEST:?required}",
            "pull_policy": "never", "restart": "no",
            "env_file": ["${APP_ENV_FILE:?private App metadata file is required}"],
            "environment": {
                prefix + "_PUBLISHER": "github-runners-host-sre",
                prefix + "_CONTROL_PLANE_HOST": "0.0.0.0",
                prefix + "_CONTROL_PLANE_STATE_DB": "/var/lib/runner-control-plane/state.db",
                prefix + "_IMAGE_PULL_POLICY": "never",
                prefix + "_CI_IMAGE_DIGEST": "${CI_IMAGE_DIGEST:?required}",
                prefix + "_GITHUB_APP_PRIVATE_KEY_PATH": "/run/secrets/github-app.pem",
                prefix + "_QUEUE_RECONCILE_INTERVAL_SECONDS": "60",
                prefix + "_QUEUE_RECONCILE_REPOS": d["repository"],
                prefix + "_GLOBAL_MAX_CONCURRENT": "1",
            },
            "ports": ["127.0.0.1:${CONTROL_PLANE_PORT:?choose an unused loopback port}:8080"],
            "volumes": [
                {"type": "bind", "source": "${DOCKER_SOCKET:?isolated or assigned Docker socket}",
                 "target": "/var/run/docker.sock", "bind": {"create_host_path": False}},
                {"type": "bind", "source": "${APP_KEY_FILE:?dedicated App private key}",
                 "target": "/run/secrets/github-app.pem", "read_only": True,
                 "bind": {"create_host_path": False}},
                "state:/var/lib/runner-control-plane",
            ],
            "networks": ["runner-egress"],
        }},
        "volumes": {"state": {}},
        "networks": {"runner-egress": {"name": d["egress_network"]}},
    }
    write("compose.yaml", encoded(compose))
    receipt = {
        "schema_version": 1, "templates_commit": revision,
        "declaration_sha256": digest(encoded(d)),
        "source_lock_sha256": digest(encoded(lock)),
        "files": {str(p.relative_to(output)): digest(p.read_bytes())
                  for p in sorted(output.rglob("*")) if p.is_file()},
        "github_e2e": "not-run", "image_build": "not-run",
    }
    write("MATERIALIZATION.json", encoded(receipt))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--templates", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=HERE / "lock.json")
    args = parser.parse_args()
    result = materialize(args.templates, args.declaration, args.output, args.lock)
    print(json.dumps({"files": len(result["files"]), "output": str(args.output)}))
