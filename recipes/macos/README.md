# Native build backend

`build(inputs, work, root, commit, *, profile)` is the macOS backend for the shared image-build front end. `profile` is `macos-ios` or `macos-flutter`; `inputs` is the object below, `work` is a **new** private evidence directory (or the front end's fresh directory containing only its matching `PLAN.json`), `root` is the Images checkout and `commit` is its exact clean recipe commit. The return value and `work/BUILD-RESULT.json` are the same JSON-serializable artifact result. Successful composition returns `status=passed`, `artifact_state=stopped-and-verified`; qualification and runtime admission remain separate. Linux owns `scripts/build-images.py` and calls this function; this backend does not edit the front end.

The backend uses `scripts/tart-layer.py` for APFS clone, boot, bounded root RPC, normal shutdown and stopped tuple sealing. It invokes the existing agent and Flutter recipes and the native SwiftLint component. It contains no executor, RPC binary, installer fork, checkpoint Python dependency or registry provisioning. The installed host owner and its approved account/storage/network binding remain external prerequisites.

## Inputs and layer order

```json
{
  "schema_version": 1,
  "name": "example-ios-build-01",
  "binding": "/absolute/approved/host-binding.json",
  "parent": {
    "directory": "/absolute/tart/vms/declared-stopped-parent",
    "manifest": "/absolute/approved/parent.manifest.json",
    "sha256": "<64 hexadecimal characters>",
    "layer": "macos-xcode-maestro"
  },
  "artifacts": {
    "swiftlint": "/absolute/offline/portable_swiftlint.zip",
    "codex": "/absolute/offline/codex",
    "codex_companion": "/absolute/offline/codex-code-mode-host",
    "claude": "/absolute/offline/claude-2.1.266-darwin-arm64",
    "grok": "/absolute/offline/grok-1.0.24-macos-aarch64"
  },
  "git": "/absolute/usable/git"
}
```

Paths are host inputs, not values to copy unchanged onto another host. They contain no secrets. The binding has the fields documented by `scripts/tart-layer.py`: actual user/UID/GID, Tart executable/home, child HOME, PATH, CPU, memory, network arguments and optional DNS. No identity or resource assignment is invented by the backend.

The logical stack is **macOS/Xcode/Simulator/Java/Maestro/SwiftLint → Codex + Claude + Grok-build together → Flutter/Dart**. A `shared-agent-build` parent reuses all four locked agent binaries and requires only `swiftlint` for iOS. Flutter from a base or agent parent additionally requires `artifacts.flutter`, the locked official SDK zip. A `flutter-dart-ios` parent reuses its locked SDK and precache receipts and requires only `swiftlint`; it is accepted only for `macos-flutter`. Reuse verifies installed locks, executable hashes, launchers and the full physical parent tuple. An overlay on an existing Flutter image adds the missing base capability without claiming to have rebuilt its earlier layers.

Every supplied archive/binary is verified again by its owning recipe inside the guest. Nothing is downloaded by the native backend. The Flutter recipe may fetch the declared iOS precache through the approved network policy; completed Flutter parents reuse that evidence. Both profiles receive the same SwiftLint binary, LICENSE, protected launcher and explicit runtime PATH. A mismatch preserves the prior image and failed derivative for reconciliation.

## Obtain the macOS/Xcode parent

The starting point is an **accountless, credential-free, neutral macOS/Xcode/Maestro Tart tuple**, with the installed canonical root RPC and permanent Python3.12 bootstrap. A Linux Dockerfile cannot create it. Reuse the verified local `macos-xcode-maestro-base-v3-20260916` catalog entry when available. Its tuple, actual physical ancestor and tool evidence are recorded in `catalog/images.json` and `provenance/native-base-20260916.json`; keep their separate identities.

On a new Mac, the host's canonical `image_build` operation owns obtaining the Apple macOS restore image, creating the Tart builder and installing the approved Xcode/iOS Simulator, Java, Maestro and bootstrap inputs. Apple downloads and license acceptance use the organization's authorized source/access; neither personal sessions nor an Xcode account may be baked into the image. Supply exact input versions, hashes, capacity and networking to that owner. This repository does not fabricate a public download or a redistributable Xcode license.

For the retained legacy prepack builder, first take a stopped COW copy with `scripts/tart-layer.py`, then follow `recipes/macos-xcode-maestro/README.md`: run its existing `neutralize.py` and `install-rpc.py` **inside the copy**, export their receipts, normally stop and seal it. The RPC bytes come from their canonical owner, not this repository. Do not point this backend at a consumer-specific executor image and call it neutral. Fresh Apple installation remains an explicit external prerequisite; this backend starts at the declared measured parent.

There is no configured remote artifact store. Final images remain on the host, `distribution=local-only`, `runtime_admission=false`, `remote_restore_verified=false`. A recipe commit is not a disk digest or a successful restore. Copying/admitting an image and changing a consumer pin remain separately owned operations.

## Run and qualify

For the shared front end, wrap the inputs object above as `{"schema_version":1,"profile":"macos-ios","inputs":{...}}` and run:

```sh
python3 scripts/build-images.py plan --profile macos-ios \
  --inputs /absolute/native-build.json --work-dir /absolute/new-build-evidence
python3 scripts/build-images.py build --profile macos-ios \
  --inputs /absolute/native-build.json --work-dir /absolute/new-build-evidence
```

The same backend can be exercised directly with the inner inputs object:

```sh
python3 recipes/macos/build.py --inputs /absolute/inputs.json \
  --work /absolute/new-build-evidence --commit <Images-commit> --profile macos-ios
```

The result records the physical parent manifest, recipe commit, installed component identities and separate final `config.json`, `nvram.bin`, `disk.img` hashes. It reuses unchanged Xcode, Simulator and Maestro evidence and does not run a customer canary. A stopped builder is not yet nonadministrator lint qualification.

```sh
python3 recipes/macos/qualify.py \
  --build-result /absolute/new-build-evidence/BUILD-RESULT.json \
  --work /absolute/new-qualification-evidence \
  --binding /absolute/approved/host-binding.json \
  --source-checkout /absolute/canonical/templates-checkout --git /absolute/usable/git
```

Qualification clones the sealed result, resolves the locked canonical `qualification-session` dependency, prepares a real nonadministrator account, normally shuts down and boots that child, and requires Aqua readiness. It runs the neutral Swift fixture through the declared PATH: the valid file must lint successfully and the deliberate force-cast violation must produce a nonzero exit and JUnit failure. It exports logs/JUnit, normally stops the child and deletes only that credential-bearing qualification VM through Tart. The sealed reusable image remains accountless. No JIT, authenticated agent session, staging secret, app build, simulator commissioning or complete canary is implied.

An existing complete consumer checkout can supply the identical locked owner blobs with `--source-kind consumer`. This uses the canonical payload resolver's existing alternative; it does not accept different modules or silently download missing blobs from a partial checkout.

## Failure and recovery

Do not rerun over a work directory or existing VM name. Every owner operation keeps its original command, timestamps, stdout/stderr and receipt. Recipe failures preserve transferred input and guest evidence; the backend attempts normal shutdown and never seals a failed build. Read `BUILD-RESULT.json`, the failed owner receipt and any `cleanup_uncertainty` before a new attempt. Reuse verified inputs and the unchanged parent; retain failed originals. Qualification cleanup has its own result and must not be inferred from lint success.

CLI console relocation belongs to the consumer's existing image preparation owner and PR322, now maintained by Linux. This backend installs no consumer CLI and cannot qualify that change.
