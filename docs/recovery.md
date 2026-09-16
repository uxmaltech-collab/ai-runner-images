# Recover or update an image without repeating commissioning

Use the installed owners and their current contracts. Historical scripts and consumed authorization receipts are evidence, not instructions to replay external effects.

## Resume an interrupted operation

1. Locate the operation's plan, source/image identities, ordered receipts and first error. Preserve all originals. Determine which step is completed, incomplete or uncertain.
2. Reconcile current state through the responsible owner: stopped/running VM, attachment and disk holders, account/service context, active job/lease and owned cleanup. Do not infer absence from a missing log or an executor state named `starting`.
3. Reuse completed stages and unchanged measurements. Execute only the missing suffix under the existing authorized scope. Never repeat a merge, transfer, enablement, job dispatch or cleanup merely because the reporting step failed.
4. Collect bounded diagnostics before shutdown or destruction. Preserve failed JUnit, partial flow and build logs, with exact provenance and sanitization. Return the first actionable result before assembling a large archive.
5. Record the actual resulting state, remaining uncertainty and recovery action. Do not replace historical failures with a later successful receipt.

## Update a small component

Use the supported stopped-image derivative operation, preserving the accepted parent. Verify exact canonical source and the full installable import/executable closure. Replace only the intended components, record old/new hashes, finalize the stopped derivative and admit its resulting identity through the existing driver. Update the executor binding through its owner while idle.

Do not reinstall Xcode for a launcher, Python module or CLI-wheel correction. Reuse unchanged tool/session evidence and run the affected source/import/ABI regressions plus the real affected execution path. A tool hash check is not a successful application build.

The current reusable images are three separate stopped derivatives: native macOS/Xcode/Maestro, the combined Codex/Claude/Grok-build layer, then Flutter/Dart. Preserve each sealed parent. Builder execution and sealing do not update the deployed executor; admission and its binding remain explicit owner operations when deployment is intended.

## Recover public tool directory permissions

The first 2026-09-16 qualification reached the real nonadministrator session but failed to execute a public tool with `PermissionError: [Errno 13]`. The builder's restrictive umask had left both `/opt/ai-runner-images` and `/opt/ai-runner-images/bin` at `0700`. Correct file ownership and executable modes inside those directories did not give the job user directory traversal. Root-only version checks had not exercised that requirement.

The canonical `recipes/macos-xcode-maestro/neutralize.py` now explicitly sets those two public directories to `0755`. For an existing affected artifact, preserve the sealed original and run `recipes/macos-xcode-maestro/repair-public-directories.py` as root inside a new accountless derivative. The repair verifies the virtual guest, absence of ordinary accounts, directory type and root ownership; it changes only those two directory modes and creates `public-directory-repair.json`. It does not recursively relax SDK permissions or alter authentication directories. Compose each subsequent layer from its corrected immutable parent.

Read back the exact directory modes, then test execution as the intended nonadministrator. A separate native APFS fixture confirmed that `clonefile` with `CLONE_NOOWNERCOPY` gives UID/GID 504 ownership of its private clone and allows chmod/write while the root-owned `0444` source remains unchanged. That isolated result verifies the file-clone primitive; it does not establish a usable guest session or a successful Flutter application build.

## Shut down normally before sealing a layer

The second composition attempt returned successful in-guest permission repair and agent installation receipts, followed by `tart stop` and stopped-image manifests. On the next derivative boot, `/opt/ai-runner-images` was again `0700`, and the repair and combined-agent installation receipts were absent. Those are observed persistence failures. The mechanism that lost the writes has not been established; do not describe it as proven APFS corruption, a cache bug or a successful repair.

Composer commit `24e82727c9509d406ed60d44dc71fde95e71550b` changes the orderly stop path to guest `/bin/sync` followed by `/sbin/shutdown -h now`. It retains a monitor of the actual Tart process and verifies its exit code is zero, plus the stopped VM state. Sealing also obtains the configuration lock, checks for disk holders and hashes the stable stopped tuple. A shutdown RPC may disconnect as the guest exits; retain that transport result and reconcile it against the process-exit and stopped-state receipts instead of treating either response alone as the result.

Use `scripts/tart-layer.py` from the pinned composition source. Set the following variables to the existing host binding, owned VM, canonical source commit, immutable parent manifest/digest and unique receipt paths from the operation plan. The boot receipt must be the completed boot of this VM with its retained `vm_exit_receipt`; do not substitute an older receipt that lacks the monitor.

```sh
python3 scripts/tart-layer.py \
  --binding "$LAYER_BINDING" --vm "$LAYER_VM" \
  --receipt "$LAYER_STOP_RECEIPT" \
  stop --boot-receipt "$LAYER_BOOT_RECEIPT"

python3 scripts/tart-layer.py \
  --binding "$LAYER_BINDING" --vm "$LAYER_VM" \
  --receipt "$LAYER_SEAL_RECEIPT" \
  seal --shutdown-receipt "$LAYER_STOP_RECEIPT" \
  --source-commit "$LAYER_SOURCE_COMMIT" \
  --parent-manifest "$LAYER_PARENT_MANIFEST" \
  --parent-digest "$LAYER_PARENT_SHA256"
```

Both receipt arguments matter: `stop --boot-receipt` records the actual process exit, and `seal --shutdown-receipt` binds the tuple to that verified normal shutdown. Do not replace an uncertain shutdown with a forced stop and label the result normal. Preserve the uncertain derivative, diagnose through its owner and continue from verified inputs.

The third composition's base completed normal shutdown with Tart exit zero; its next derivative boot read back the persisted directory repair (`agents-v3-parent-readback.1.stdout`). This proves that specific persistence check. Nonadministrator engine execution, Flutter application build and simulator UI acceptance still require their own completed qualification receipts.

Keep the first attempt's `base-seal.manifest.json`, `agents-seal.manifest.json` and `flutter-seal.manifest.json`, the second attempt's `base-v2-seal.manifest.json` and `agents-v2-seal.manifest.json`, and their failed execution/readback evidence. The unfinished second Flutter derivative has no completed seal to invent. Later manifests identify new artifacts; they do not replace those historical records or retroactively qualify them.

## Recover Flutter precache after a network failure

On 2026-09-16 the initial builder could not resolve `pub.dev`. The builder had inherited a private DHCP DNS server, while its existing network policy allowed public egress. The thin builder path had omitted the installed executor's guest-DNS setup. The approved binding already supplied the remedy: service `Ethernet`, servers `8.8.4.4` and `8.8.8.8`. No network-policy expansion was needed.

For another host, read that host's installed DNS declaration instead of copying these values by default. Inspect the guest's current resolver and retain the failed command's output. Apply the declared servers once inside the unfinished builder through its existing root RPC, then read them back exactly:

```sh
/usr/sbin/networksetup -setdnsservers Ethernet 8.8.4.4 8.8.8.8
/usr/sbin/networksetup -getdnsservers Ethernet
```

These are the commands used for this recorded binding, not a host-wide change. Check name resolution and the required package endpoints separately; an HTTP error response can prove transport reached a server without proving the package operation succeeded. The installed executor's DNS setup also verifies the configured servers after guest restart. Preserve stopped sealed parents while diagnosing a derivative.

The installer supports resuming this exact failure class. Recover the staging path and previous evidence directory from the failed receipt. Keep the original ZIP and evidence, then run the same pinned recipe inside the builder with a new evidence directory:

```sh
/opt/macos-tart-bootstrap/python/bin/python3.12 -I -B /tmp/flutter-dart/install.py \
  --archive /tmp/flutter_macos_arm64_3.47.4-stable.zip \
  --runtime-python /opt/macos-tart-bootstrap/python/bin/python3.12 \
  --resume-stage /opt/ai-runner-images/.flutter-incoming-RECOVERED-ID \
  --prior-evidence-dir /opt/ai-runner-images/flutter-installation \
  --evidence-dir /opt/ai-runner-images/flutter-installation-recovery
```

Replace `RECOVERED-ID` and any transfer/evidence paths with the preserved operation's actual paths. The resume code binds the prior archive-verification record to the recipe pin, checks the preserved Flutter/Dart revisions, compares executable entry scripts with the retained archive and records the original logs. It does not extract the SDK again or repeat completed analytics configuration. It reruns iOS precache, version checks and SDK sealing. The 2026-09-16 recovery completed these steps and retained the original `Failed to update packages` log. A new stopped Tart artifact manifest then identified the completed image; SDK sealing alone is not a Tart image seal.

## Recover a user's Flutter cache

The sealed SDK and public pub-cache seed remain root-owned under `/opt/ai-runner-images/flutter/3.47.4`. The launcher creates a writable APFS clone under the nonadministrator job's canonical HOME, keyed by `SDK-READY.json`'s digest. `CLONE-RECEIPT.json` identifies the seed, owner and file-clone counts. Reuse a completed matching clone.

An interrupted clone leaves its temporary directory for inspection. Preserve that directory and its first error before retrying; do not overwrite a completed clone or modify the shared seed. If `clonefile(2)` reports a filesystem mismatch, choose the job's declared private work root on the SDK's filesystem. The launcher deliberately does not fall back to a large full copy. The job's quota must cover later private SDK/cache writes and project build outputs.

A new seed gets a different cache directory. Clean only the completed job's assigned HOME/work resources through its owner. There is no automatic cross-user cache pruning. Agent authentication is unrelated to SDK cache repair: Codex, Claude and Grok-build remain installed together, while credentials and private configuration arrive only for the authorized job.

## Restore on another machine

Retrieve source at the recorded commits and tool/image artifacts through the declared distribution mechanism. Verify the complete manifest and bytes, then obtain a restore receipt. The current accepted EnviaFlores reference is cataloged as local-only: do not invent a registry URL or treat its disk hash as an OCI manifest.

Commission a new host through the canonical host owner using its actual account, service ACL, home/keychain, APFS and SSH declarations. A successful key offer is not complete authentication; verify the account/PAM/service context and dedicated endpoint. Preserve unrelated host accounts and services.

The private commissioning archive is separate from this repository. Local paths and digest indexes identify evidence but do not make it remotely recoverable. Archive publication, retention and readback must have real receipts before claiming portable historical preservation.

## Common diagnosis boundaries

| Symptom | First responsible surface |
| --- | --- |
| SSH accepts a key then disconnects | Native account/PAM/service ACL and intended shell; preserve server diagnostics |
| Service cannot use its keychain | Directory Services home, service HOME, keychain ownership and current startup receipt |
| Guest child spawn fails or diagnostics disappear | RPC descriptor lifecycle, actual inherited FDs and first-error retention |
| Flutter precache cannot resolve package hosts | Installed guest DNS binding, effective resolver and existing egress policy; preserve and resume the verified extraction |
| Flutter cannot create its writable SDK | Canonical user-owned HOME, seed/clone receipts, APFS filesystem and available job storage |
| Codex launches but tools fail | Complete engine companion closure, PATH and effective noninteractive MCP permissions |
| Build passes but staging check fails | Compiled app's environment semantics and URL construction, not automatic image rebuild |
| Maestro assertion fails | Observed locale, overlays, accessibility and application state; retain the failed result |
| Flow exists but delivery fails | Driver/publisher contract, optional-artifact policy, exact flow bytes and commit identity |
| Media omitted for size | Bounded export/encoding and verified private retention; keep available evidence moving |

Do not claim `originals_preserved` establishes recoverability after cleanup without a verified retained copy. Read the detailed [failure catalog](research/2026-09-16/LESSONS-AND-FAILURES.md) before repeating a previously diagnosed commissioning problem.
