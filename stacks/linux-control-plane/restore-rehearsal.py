#!/usr/bin/env python3
"""Cold-import a verified archive into a disposable, network-disabled daemon.

Requires Linux root and dockerd. Uses no existing Docker socket/store, host
firewall rules, App credentials, runner registration or production container.
All runner probes are offline. This is restoration/boot evidence, not E2E.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rehearse(receipt_path: Path, declaration: Path, evidence: Path):
    if os.geteuid() != 0:
        raise ValueError("isolated dockerd rehearsal requires root")
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = json.loads(receipt_path.read_text())
    d = json.loads(declaration.read_text())
    if sha(declaration) != receipt["declaration_sha256"]:
        raise ValueError("declaration does not match the build")
    archive = receipt_path.parent / receipt["archive"]["name"]
    if archive.stat().st_size != receipt["archive"]["bytes"] or sha(archive) != receipt["archive"]["sha256"]:
        raise ValueError("archive size or digest mismatch")
    # A short private Unix socket path avoids sockaddr_un's length limit.
    runtime = Path(tempfile.mkdtemp(prefix="runner-restore-"))
    socket = runtime / "docker.sock"
    config = runtime / "daemon.json"
    config.write_text(json.dumps({"features": {"containerd-snapshotter": True}}))
    command = ["dockerd", "--config-file", str(config), "--data-root", str(evidence / "store"),
               "--exec-root", str(runtime / "run"), "--pidfile", str(runtime / "daemon.pid"),
               "--containerd", str(runtime / "containerd.sock"),
               "--containerd-namespace", runtime.name,
               "--containerd-plugins-namespace", runtime.name + "-plugins",
               "--host", "unix://" + str(socket), "--bridge", "none", "--iptables=false",
               "--ip6tables=false", "--ip-forward=false", "--ip-masq=false"]
    (evidence / "daemon-command.json").write_text(json.dumps(command, indent=2) + "\n")
    # Do not inherit another tenant's Docker context, API token or proxy settings.
    env = {"PATH": os.environ["PATH"], "HOME": str(runtime), "DOCKER_CONFIG": str(runtime / "client")}
    client = ["docker", "--host", "unix://" + str(socket)]
    # Separate data roots and --bridge none do NOT isolate libnetwork from
    # host links. Both daemons must run in a different network namespace.
    namespace = subprocess.Popen(["unshare", "--net", "--", "sleep", "infinity"], env=env)
    for _ in range(40):
        if namespace.poll() is not None:
            raise RuntimeError("network namespace owner exited")
        own_namespace = Path(f"/proc/{namespace.pid}/ns/net")
        if os.readlink(own_namespace) != os.readlink("/proc/self/ns/net"):
            break
        time.sleep(0.05)
    else:
        namespace.terminate()
        namespace.wait(timeout=5)
        raise RuntimeError("refusing to start a test daemon in the host network namespace")
    isolated = ["nsenter", "--target", str(namespace.pid), "--net", "--"]
    subprocess.run(isolated + ["ip", "link", "set", "lo", "up"], check=True, env=env)
    containerd_log = (evidence / "containerd.log").open("x")
    containerd_command = isolated + ["containerd", "--config", "/dev/null", "--address", str(runtime / "containerd.sock"),
                          "--root", str(evidence / "containerd"), "--state", str(runtime / "containerd-state")]
    (evidence / "containerd-command.json").write_text(json.dumps(containerd_command, indent=2) + "\n")
    containerd = subprocess.Popen(containerd_command, stdout=containerd_log, stderr=subprocess.STDOUT, env=env)
    log = (evidence / "daemon.log").open("x")
    daemon = subprocess.Popen(isolated + command, stdout=log, stderr=subprocess.STDOUT, env=env)
    cp = None
    result = {"schema_version": 1, "build_receipt_sha256": sha(receipt_path),
              "archive_sha256": sha(archive), "initial_store": "new-empty-directory",
              "network_namespace": os.readlink(own_namespace),
              "host_network_namespace": os.readlink("/proc/self/ns/net"),
              "github_e2e": "not-run", "credentials": "none", "images": {}, "status": "failed"}

    def docker(args, *, timeout=180):
        return subprocess.check_output(client + args, stderr=subprocess.STDOUT, env=env, timeout=timeout)

    try:
        for _ in range(60):
            if daemon.poll() is not None:
                raise RuntimeError("isolated daemon exited; see daemon.log")
            if socket.exists():
                try:
                    docker(["info"], timeout=2)
                    break
                except (subprocess.SubprocessError, OSError):
                    pass
            time.sleep(0.5)
        else:
            raise RuntimeError("isolated daemon did not become ready")
        initial = docker(["image", "ls", "-q"]).decode().splitlines()
        if initial:
            raise ValueError("restoration requires an actually empty image store")
        (evidence / "load.log").write_bytes(docker(["image", "load", "-i", str(archive)], timeout=600))
        for name, expected in receipt["images"].items():
            observed = json.loads(docker(["image", "inspect", expected["reference"]]))[0]
            if observed["Id"] != expected["id"] or observed["RootFS"]["Layers"] != expected["layers"]:
                raise ValueError(f"restored image identity mismatch: {name}")
            result["images"][name] = {"reference": expected["reference"], "identity": "matched"}
        leaf = receipt["images"]["runner-" + d["profile_id"]]["reference"]
        uid = docker(["run", "--rm", "--pull", "never", "--network", "none", "--entrypoint", "id", leaf, "-u"]).strip()
        if uid != b"1001":
            raise ValueError("restored runner is not UID 1001")
        agents = receipt["images"]["runner-agent-base"]["reference"]
        for harness in ("claude", "codex", "grok"):
            raw = docker(["run", "--rm", "--pull", "never", "--network", "none", "--user", "runner",
                          "--entrypoint", harness, agents, "--version"])
            (evidence / f"{harness}.log").write_bytes(raw)
        prefix = d["environment_prefix"]
        settings = {
            "PUBLISHER": "github-runners-host-sre", "CONTROL_PLANE_HOST": "127.0.0.1",
            "CI_IMAGE_DIGEST": leaf.split("@", 1)[1], "IMAGE_PULL_POLICY": "never",
            "GITHUB_APP_ID": "1", "GITHUB_APP_SLUG": "offline-fixture",
            "GITHUB_APP_ORGANIZATION": d["organization"],
            "GITHUB_APP_PRIVATE_KEY_PATH": "/not-provisioned/offline-fixture.pem",
            "GITHUB_API_URL": "http://127.0.0.1:9", "QUEUE_RECONCILE_INTERVAL_SECONDS": "0",
        }
        args = ["run", "--detach", "--pull", "never", "--network", "none"]
        for key, value in settings.items():
            args += ["--env", prefix + "_" + key + "=" + value]
        args += [receipt["images"]["runner-control-plane"]["reference"]]
        cp = docker(args).decode().strip()
        probe = "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).read().decode())"
        for _ in range(20):
            try:
                health = json.loads(docker(["exec", cp, "python", "-c", probe], timeout=5))
                break
            except subprocess.SubprocessError:
                time.sleep(0.5)
        else:
            raise RuntimeError("restored control plane did not pass health")
        if health["status"] != "ok" or health["profiles"] != 1:
            raise ValueError("unexpected control-plane health")
        (evidence / "health.json").write_text(json.dumps(health, indent=2) + "\n")
        result.update(status="passed", runner_uid=1001, control_plane_boot="passed-offline",
                      harness_versions="passed-offline-unprivileged")
    finally:
        if cp:
            try:
                (evidence / "control-plane.log").write_bytes(docker(["logs", cp]))
                docker(["stop", "--time", "10", cp])
                docker(["rm", cp])
                result["containers_remaining"] = docker(["ps", "-aq"]).decode().splitlines()
            except subprocess.SubprocessError:
                result["status"] = "cleanup-failed"
        daemon.terminate()
        try:
            daemon.wait(timeout=30)
        except subprocess.TimeoutExpired:
            result["status"] = "cleanup-failed"
            # Leave evidence and the owned process visible, never kill by name.
        log.close()
        containerd.terminate()
        try:
            containerd.wait(timeout=30)
        except subprocess.TimeoutExpired:
            result["status"] = "cleanup-failed"
        containerd_log.close()
        result["daemon_stopped"] = daemon.poll() is not None
        result["containerd_stopped"] = containerd.poll() is not None
        namespace.terminate()
        namespace.wait(timeout=5)
        result["network_namespace_owner_stopped"] = namespace.poll() is not None
        result["runtime_directory"] = str(runtime)
        (evidence / "RESTORE.json").write_text(json.dumps(result, indent=2) + "\n")
    if result["status"] != "passed" or not result["daemon_stopped"] or not result["containerd_stopped"] or result.get("containers_remaining"):
        raise RuntimeError("restoration or owned cleanup failed; see RESTORE.json")
    print(str(evidence / "RESTORE.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    rehearse(args.build_receipt.resolve(), args.declaration.resolve(), args.evidence.resolve())
