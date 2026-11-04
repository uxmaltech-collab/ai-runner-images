# Flutter and Dart layer

This layer inherits the complete `agent-build` layer: Codex, Claude Code and Grok Build remain present together. It adds Flutter **3.47.4**, framework revision `9584c6713b324636289d067944a46fd6b49df14b`, and Dart **3.13.3**. The release pin is in `pins.json` and comes from the [official macOS release metadata](https://storage.googleapis.com/flutter_infra_release/releases/releases_macos.json).

The 2,261,358,207-byte archive expands to 4,357,895,113 bytes across 23,295 entries. It already contains iOS engine artifacts; the installation still executes `flutter precache --ios` and records its actual outcome. The [Flutter CLI reference](https://docs.flutter.dev/reference/flutter-cli) documents precache and the usual build commands. Xcode, its selected developer directory, iOS runtime, Simulator, Java and Maestro belong to the native parent recipe. This layer does not create accounts, start VMs, alter the executor or configure an agent account.

## Root installation in the builder guest

The image owner transfers this recipe directory and the verified archive to its existing builder. Run as root inside that guest; no ordinary guest account is required during image composition. Use the permanent Python interpreter already supplied by the parent, not an interpreter inside a temporary transfer directory:

```sh
python3 /tmp/flutter-dart/install.py \
  --archive /tmp/flutter_macos_arm64_3.47.4-stable.zip \
  --runtime-python /usr/bin/python3 \
  --evidence-dir /var/tmp/flutter-installation-01
```

`--runtime-python` is an explicit image binding; substitute the parent's actual permanent interpreter if it differs. The installer verifies the full archive digest, archive paths, entry types, symlink containment and bundled framework/Dart revisions before extracting. It then requires the parent's complete agent layer: the launchers of all three engines and the harness pins receipt that layer was installed from.

The installer uses a newly created staging directory under `/opt/ai-runner-images`, with separate temporary HOME and pub cache paths. It disables Flutter/Dart analytics for this operation and runs only extraction, analytics configuration, iOS precache and version inspection. It preserves logs, pins, exact commands and byte hashes. No credentials, personal dotfiles or user repository caches are consulted. A failed operation leaves its own staging tree and evidence for recovery; it does not erase or replace a previous SDK.

The final seed is `/opt/ai-runner-images/flutter/3.47.4/sdk`. The public dependency-cache seed is beside it at `pub-cache-seed`. Both are root-owned; regular files are 0444 or 0555 and directories are 0555. `SDK-MANIFEST.json` records the complete regular-file hashes and symlink targets. `SDK-READY.json` is written only after successful precache/version checks and binds that manifest. The installer removes its temporary HOME before reporting completion. Its receipt is `INSTALLATION-RECEIPT.json` in the specified evidence directory.

Export the receipt and logs before removing only the transfer and evidence copies owned by this build. The owning image operation finalizes disk/config/NVRAM identities and seals the layer. Do not place job credentials in the image.

## Writable SDKs for nonadministrator jobs

Set the job's declared PATH to include:

```text
/opt/ai-runner-images/flutter/bin
/opt/ai-runner-images/agents/bin
```

The `flutter` and `dart` launchers require a non-root macOS arm64 user and the job's canonical, user-owned HOME. On first use they clone the sealed SDK and pub-cache seed into:

```text
$HOME/Library/Caches/ai-runner-images/flutter-3.47.4-<seed-ready-sha256-first-16>/sdk
$HOME/Library/Caches/ai-runner-images/flutter-3.47.4-<seed-ready-sha256-first-16>/pub-cache
```

`AI_RUNNER_FLUTTER_WORK_ROOT` can select an explicit private directory on the same filesystem instead. Each copied regular file uses Apple's `clonefile(2)` with caller ownership, so the SDK data blocks are shared until modified. There is no silent full-copy fallback. [Apple's clonefile contract](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/man/man2/clonefile.2) specifies private writes, exclusive creation and failure across filesystems. This keeps user caches writable while the root seed remains unchanged. A completed `CLONE-RECEIPT.json` records the seed digest, owner and actual file-clone counts.

Initialization is serialized per user/seed. Existing completed clones are reused; partial staging directories and mismatched receipts are preserved for explicit reconciliation. A different sealed seed receives a different cache directory. Neither normal startup nor recovery overwrites an older clone. Clone storage grows as the job writes; account for those writes and project build outputs within the job's existing quota. Cleanup removes only the completed job's assigned HOME/work directories through the owner operation; there is no timer or cross-user cache deletion.

The launcher sets `FLUTTER_ROOT` and `PUB_CACHE` to the writable copy and passes `--suppress-analytics` to both Flutter and Dart. It never enables analytics or creates an agent session. Package fetching, project source, credentials and model configuration remain the job owner's inputs.

## Qualification after sealing

Darwin checks symlink permissions when a nonadministrator calls `readlink(2)`. The SDK seal therefore gives public symlinks mode `0555`, records their modes and preserves their targets. A restrictive builder umask previously left 17 root-owned links at `0700`; real nonadministrator Flutter startup failed while cloning those links. A regular-file-only APFS clone test did not cover this case.

For an affected sealed SDK, preserve its parent and run this bounded repair inside a **new accountless derivative**. Stage `repair-symlink-modes.py` and `pins.json` together. Supply the actual previous `SDK-READY.json` digest from the retained installation receipt and a fresh private evidence directory:

```sh
/opt/macos-tart-bootstrap/python/bin/python3.12 -I -B \
  /tmp/flutter-dart/repair-symlink-modes.py \
  --expected-ready-sha256 "$PREVIOUS_SDK_READY_SHA256" \
  --evidence-dir /opt/ai-runner-images/flutter-symlink-repair
```

The repair verifies the full existing regular-file inventory and SHA-256 values, exact symlink targets and seed identity before changing anything. It preserves the original SDK manifest and ready marker in the private evidence directory, records an intent, changes only symlink modes and reissues both metadata files with new digests. It does not download, extract, precache, create accounts or alter regular SDK payloads. If interrupted, reconcile the intent and metadata before another mutation. The resulting derivative still needs normal shutdown, its own stopped-image manifest and the intended nonadministrator qualification; the repair receipt alone does not qualify it.

The image owner creates a disposable qualification clone and uses its intended nonadministrator job user. It does not add a qualification account to the sealed base image. With the declared PATH, run:

```sh
flutter --version --machine
dart --version
flutter create --platforms=ios --org com.uxmaltech.fixture hello_world
cd hello_world
flutter build ios --simulator --debug
```

Retain the version output, clone receipt, actual Hello World build result and owned cleanup. Verify that the SDK seed manifest remains unchanged and that the user's clone/cache can be written. Flutter's SDK is intentionally mutable only in the user copy; do not run `flutter upgrade` against the shared seed. Installing and exercising the resulting app through Simulator/Maestro belongs to the qualification owner. A neutral fixture qualifies image mechanics and does not establish a customer's staging journey.

Offline recipe preparation can inspect the actual ZIP without extraction, installation, account changes or Flutter execution:

```sh
python3 recipes/flutter-dart/install.py \
  --inspect-only \
  --archive /absolute/path/flutter_macos_arm64_3.47.4-stable.zip \
  --evidence-dir /absolute/path/new-archive-inspection
```

The installer and launcher preserve original errors and partial evidence. Inspection, isolated clone mechanics and source review do not establish successful guest installation, iOS precache, a simulator build or final image qualification.
