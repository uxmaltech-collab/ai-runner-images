# Canonical image builder qualification

The Android profile ran through `scripts/build-images.py` from committed source.
It verified and reused the unchanged combined-agent parent, built the neutral
Android recipe, exported a local archive and restored into an empty independent
Docker/containerd store in a separate network namespace. Image ID and every
layer matched. Tools and all three harnesses launched offline as UID 1001.
All owned processes stopped, no fixture containers remained and the host bridge
was preserved. No production runner or service was restarted.

`SUMMARY.json` binds the tested orchestration and recipe commits, inputs and
original evidence digests. `android-build.json` and `android-restore.json` are
the original build/restore receipts. Tool logs are retained. The 4 GB local
archive is deliberately outside Git. It does not require remote storage.

This verifies image construction and cold restoration. It does not credit a new
application build, emulator boot or authenticated agent job. The accepted mobile
application E2Es remain separate evidence. Native backend qualification is pending
Mac; no complete clean-machine macOS reconstruction is claimed.

The `linux-control-plane` profile also ran through the same entrypoint: pinned
materialization, all four image builds, local archive export, an empty isolated
restore store, UID 1001 harness probes and a real offline control-plane health
check. All four identities/layers matched and owned processes/containers stopped.
See `linux-build.json`, `linux-restore.json` and `linux-health.json`. No App token
or production Docker socket was mounted. This is image qualification, not a new
GitHub dispatch.
