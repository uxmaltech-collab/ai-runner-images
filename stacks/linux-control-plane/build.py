#!/usr/bin/env python3
"""Build only the materialized stack, then preserve its immutable OCI archive.

This creates task-owned images, not a deployment. It never starts a control
plane, registers a GitHub runner, reads credentials or touches another image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(argv, log: Path, **kwargs):
    with log.open("x") as f:
        result = subprocess.run(argv, stdout=f, stderr=subprocess.STDOUT, **kwargs)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}); preserved log: {log}")


def build(pack: Path, evidence: Path, *, download: bool):
    pack = pack.resolve()
    lock = json.loads((pack / "source-lock.json").read_text())
    materialization = json.loads((pack / "MATERIALIZATION.json").read_text())
    for name, expected in materialization["files"].items():
        if sha(pack / name) != expected:
            raise ValueError(f"materialization changed: {name}")
    d = json.loads((pack / "declaration.json").read_text())
    revision = lock["templates"]["commit"]
    evidence.mkdir(parents=True, exist_ok=False)
    # The root images must already be supplied; an absent root is not silently pulled.
    for role, ref in lock["roots"].items():
        if "@sha256:" not in ref:
            raise ValueError("root images must be immutable")
        run(["docker", "image", "inspect", ref], evidence / f"root-{role}.json")
    wheelhouse = pack / "wheelhouse"
    wheelhouse.mkdir(exist_ok=True)
    requirements = pack / "requirements.lock"
    if download:
        run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
             "--require-hashes", "--dest", str(wheelhouse), "-r", str(requirements)],
            evidence / "download-wheels.log")
    wheel_lock = json.loads((pack / "wheels.lock.json").read_text())
    if {p.name for p in wheelhouse.iterdir()} != {i["file"] for i in wheel_lock}:
        raise ValueError("wheelhouse must contain exactly the locked artifacts")
    for item in wheel_lock:
        if sha(wheelhouse / item["file"]) != item["sha256"]:
            raise ValueError(f"wheel digest mismatch: {item['file']}")
    (pack / "requirements.lock").write_bytes(requirements.read_bytes())
    images = {}
    input_tag = revision[:12] + "-" + sha(pack / "MATERIALIZATION.json")[:16]

    def image(name, dockerfile, args, target=None):
        tag = f"{d['image_namespace']}/{name}:{input_tag}"
        command = ["docker", "buildx", "build", "--load", "--provenance=false",
                   "--platform", lock["platform"], "--tag", tag, "--file", dockerfile]
        if target:
            command += ["--target", target]
        # BuildKit does not resolve a locally built manifest by digest alone.
        # Bind the immutable parent to the just-inspected local tag, retaining
        # the digest-qualified FROM and preventing accidental registry lookup.
        for parent in images.values():
            if parent["reference"] in args.values():
                observed = json.loads(subprocess.check_output([
                    "docker", "image", "inspect", parent["tag"]]))[0]
                if parent["reference"] not in observed["RepoDigests"]:
                    raise ValueError("local parent tag changed before build")
                command += ["--build-context", parent["reference"] + "=docker-image://" + parent["tag"]]
        for key, value in sorted(args.items()):
            command += ["--build-arg", f"{key}={value}"]
        command.append(".")
        (evidence / f"{name}.command.json").write_text(json.dumps(command, indent=2) + "\n")
        run(command, evidence / f"{name}.build.log", cwd=pack)
        info = json.loads(subprocess.check_output(["docker", "image", "inspect", tag]))[0]
        repository = tag.rsplit(":", 1)[0]
        refs = [x for x in info["RepoDigests"] if x.startswith(repository + "@sha256:")]
        if len(refs) != 1:
            raise ValueError(f"build did not produce a unique immutable reference for {name}")
        images[name] = {"tag": tag, "reference": refs[0], "id": info["Id"],
                        "architecture": info["Architecture"], "layers": info["RootFS"]["Layers"]}
        (evidence / "images.partial.json").write_text(json.dumps(images, indent=2) + "\n")
        print(f"built {name}: {refs[0]}", flush=True)
        return refs[0]

    args = {k: v for k, v in lock["build_args"].items() if not k.startswith("GROK_")}
    args.update(RUNNER_BASE_OS_IMAGE=lock["roots"]["os"], RUNNER_BASE_REVISION=revision,
                JIT_CONFIG_ENV=d["environment_prefix"] + "_JIT_CONFIG")
    base = image("runner-base", "containers/runner-base/Dockerfile", args)
    agents = image("runner-agent-base", "containers/runner-agent-base/Dockerfile", {
        "RUNNER_BASE_IMAGE": base, "RUNNER_BASE_REVISION": revision,
        "GROK_INSTALLER_SHA256": lock["build_args"]["GROK_INSTALLER_SHA256"],
        **{f"{engine}_VERSION": lock["harness_versions"][key] for engine, key in
           (("CLAUDE_CODE", "claude"), ("CODEX_CLI", "codex"), ("GROK_CLI", "grok"))},
    }, target="agents")
    leaf = "runner-" + d["profile_id"]
    image(leaf, f"runners/images/{leaf}/Dockerfile", {"RUNNER_BASE_IMAGE": base})
    image("runner-control-plane", "runners/control-plane/Dockerfile", {
        "RUNNER_BASE_IMAGE": base, "PYTHON_BASE_IMAGE": lock["roots"]["python"],
        "SOURCE_REVISION": revision,
    })
    for engine in ("claude", "codex", "grok"):
        run(["docker", "run", "--rm", "--pull", "never", "--network", "none",
             "--user", "runner", "--entrypoint", engine, agents, "--version"],
            evidence / f"{engine}.version.log")
        reported = (evidence / f"{engine}.version.log").read_text()
        expected_version = lock["harness_versions"][engine]
        if not re.search(r"(?<![0-9.])" + re.escape(expected_version) + r"(?![0-9.])", reported):
            raise ValueError(f"{engine} did not report its locked version")
    for name, info in images.items():
        run(["docker", "run", "--rm", "--pull", "never", "--network", "none",
             "--entrypoint", "dpkg-query", info["reference"], "-W",
             "-f=${Package}\t${Version}\t${Architecture}\n"], evidence / f"{name}.packages.tsv")
    archive = evidence / "images.tar"
    run(["docker", "image", "save", "--output", str(archive),
         *[v["tag"] for v in images.values()]], evidence / "save.log")
    receipt = {
        "schema_version": 1, "templates_commit": revision, "platform": lock["platform"],
        "declaration_sha256": sha(pack / "declaration.json"),
        "materialization_sha256": sha(pack / "MATERIALIZATION.json"),
        "requirements_sha256": sha(requirements), "images": images,
        "archive": {"name": archive.name, "bytes": archive.stat().st_size, "sha256": sha(archive)},
        "qualification": {"harness_versions": "passed-offline-unprivileged",
                          "github_e2e": "not-run", "restore": "not-run",
                          "authenticated_agents": "not-run"},
        "rebuild_limitations": lock["limitations"],
    }
    (evidence / "BUILD.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(evidence / "BUILD.json"), "archive_bytes": archive.stat().st_size}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--download-wheels", action="store_true")
    args = parser.parse_args()
    build(args.pack, args.evidence.resolve(), download=args.download_wheels)
