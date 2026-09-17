# AI runner images

The shared home for **all runner images and tools** across **iOS/macOS, Android, Linux, web and future platforms**, reusable across organizations and repositories. This includes image recipes, tool installers and launchers, compatibility locks, artifact identities, qualification evidence and operating knowledge for `resolver`, `create-journey`, `test-e2e` and other supported jobs.

## Platform scope

| Platform | Image and tool scope | Current evidence in this repository |
| --- | --- | --- |
| iOS/macOS | Tart, macOS, Xcode, Simulator, Java, Maestro, the combined agent layer and optional Flutter/Dart support | Flutter iOS Hello World image qualified; exact local artifacts and receipts recorded |
| Android | Linux base, Android SDK/emulator, Java, Maestro, the combined agent layer and optional Flutter/Dart support | In scope; image implementation and qualification pending |
| Linux | Linux runner bases, the combined agent layer, build toolchains and job utilities | Portable CI stack built and cold-restored; real GitHub E2E pending |
| Web | Linux runner capabilities for browsers and Playwright, using the combined agent layer | In scope; image implementation and qualification pending |

The [platform catalog](catalog/platforms.json) records scope and demonstrated status separately. The [platform guide](docs/platforms.md) describes how images and tools are organized. iOS is the first qualified implementation; the repository is not limited to Apple or Flutter workloads.

## First qualified composition: Flutter iOS

The iOS image uses this exact composition:

1. **Tart macOS/Xcode/Maestro base**, including iOS Simulator and required platform runtimes such as Java.
2. **One agent-build layer containing Codex, Claude and Grok-build together**, with their complete runtime/companion dependencies.
3. **Flutter/Dart support**, including the pinned iOS toolchain artifacts needed for a small iOS Hello World qualification.

Each layer records its exact parent digest. Engines are installed together in the shared agent layer; authentication is supplied only to authorized jobs and never sealed into any layer.

This repository owns image and toolchain composition and its qualification records. The existing executor, guest/session/RPC protocol, ordinary resolver and external publisher remain in their canonical owners. Platform recipes consume those canonical components and supply the tools needed by the existing jobs.

## Promoted mobile knowledge

The [neutral Android recipe](recipes/android/README.md) retains the exercised
consumer toolchain with organization bindings removed. Its extracted source has
regression coverage; a new neutral image build is not claimed. Current accepted
iOS/Android references are appended in [the catalog](catalog/images.json), keeping
the original records. Read [operating lessons](docs/operating-lessons.md) for
qualification, recording and honest distribution/restore status.

## Current status

| Entry | Evidence and limits |
| --- | --- |
| Native macOS/Xcode/Maestro base | Sealed v3 base: macOS 26.6.2, Xcode 26.5, iOS Simulator 26.5, Maestro 2.10.0 and Java 17. Its tools passed qualification in the final Flutter derivative's nonadministrator Aqua session. |
| Shared Codex + Claude + Grok-build layer | All three engines are installed together: Codex 0.151.0 and its companion, Claude 2.1.266 and Grok-build 1.0.24. Exact payload hashes and all three native CLI launches passed as UID 502. Authentication remains job-time configuration. |
| Flutter/Dart layer | Sealed v4 image with Flutter 3.47.4 and Dart 3.13.3. A fresh nonadministrator SDK clone built the real iOS Hello World app, installed and launched it on an isolated iPhone 17 / iOS 26.5 simulator, and passed Maestro assertions. Simulator and qualification VM cleanup are verified. |
| EnviaFlores native iOS reference | Canary #2343 completed exploration, staging build, Maestro smoke/journey, delivered-flow replay, verified external publication and cleanup. Its image contains the EnviaFlores pack and app-specific driver; it is a historical consumer-specific reference, not the neutral base's direct parent. |
| Lastmile application integration | Source discovery completed for the host app, driver package and direct shared dependencies. The app requests absent driver ref `v0.5.1`; no Lastmile Flutter build is claimed. |

The three current Flutter iOS logical layers have these artifact-manifest SHA-256 identities:

```text
native base 2a77a0c4faed3dcbf9524d6c9238eddaa1cddce0af9b130f8f0577d76d69eceb
all agents  2e1c0f79e7b14ed43d811824507af63472885a0cbf49df86ee2071de3977227d
Flutter     33fb89bdccd573057c11388bdf2dc243fbf8a4d5ceea46d2c577c93e2e2dd9be
```

The [image catalog](catalog/images.json) and [composition record](docs/image-composition.md) distinguish source provenance, installation and qualification. These artifacts are currently local to the Mac; the manifest hashes are not OCI references. No executor admission or production binding change is implied by sealing a layer. The [accepted native reference](provenance/accepted-enviaflores-ios.json) records the historical canary's separate image, app/flow commit and publication evidence.

The [Hello World qualification](qualification/flutter-ios-hello-world-20260916/README.md) records the real build, all-engine CLI checks, JUnit, screenshots, exact fixture inputs and cleanup. Maestro verified `Hello World`, `Count: 0`, the `Increment` action and `Count: 1`: one test, zero failures. The image has no authenticated agent session, and this neutral fixture does not establish Lastmile staging acceptance.

The catalog preserves physical repair ancestry separately from those three logical capabilities. Earlier images with public-directory, shutdown-persistence or SDK-symlink failures remain historical ineligible records. The successful qualification uses the exact v4 image above; it does not retroactively validate those failed attempts.

## Where to start

For Linux control-plane portability, use the
[materialized stack and image archive rehearsal](stacks/linux-control-plane/README.md).
**`collab-e2e-org` is the designated organization for real cross-organization
E2E qualification**, with `collab-e2e-org/collab-delivery` as the runner canary
repository. Its App, runner group and runtime state are separate from consumer
organizations. The declaration is an example binding, not an engine default.

1. Read [architecture](docs/architecture.md) and [ownership](docs/ownership.md) before changing an image or shared component.
2. Select a recipe and its exact compatibility lock. Use its documented owner operations; preserve the accepted parent and create a distinct derivative.
3. Record real qualification results under `qualification/`. Update the catalog only from completed receipts, preserving failed attempts and limitations.
4. Use [recovery](docs/recovery.md) to reconcile interrupted work and execute only unfinished operations.

Start with the [native base](recipes/macos-xcode-maestro/README.md), [combined agent layer](recipes/agent-build/README.md) and [Flutter/Dart recipe](recipes/flutter-dart/README.md). The thin composition tool preserves the source image and records each derivative's parent, commands and stopped artifact identities. Executor installation, admission and repository routing retain their existing owners.

## Flutter in a job

The image contains a root-owned, read-only Flutter SDK and public dependency-cache seed. A nonadministrator job uses `/opt/ai-runner-images/flutter/bin` and `/opt/ai-runner-images/agents/bin` on its declared PATH. The Flutter launcher creates a private APFS clone under that user's canonical HOME, keyed by the sealed seed digest, and reuses the completed clone on subsequent invocations. SDK/cache writes remain private to that job user. The launcher has no full-copy fallback; an alternate work root must be on the SDK's filesystem.

The [recipe](recipes/flutter-dart/README.md) gives the paths, commands, clone receipt and cleanup ownership. Agent authentication, model settings and private repository environments arrive through the job's existing managed delivery. The image contains no authenticated agent session.

The initial Flutter precache exposed a missing builder DNS step: the public network policy excluded the inherited private DHCP resolver. Applying the installed binding's public DNS servers inside the unfinished builder restored resolution. Recovery reused the verified extraction, preserved the failed log and reran only precache/version/seal; see [the recovery procedure](docs/recovery.md#recover-flutter-precache-after-a-network-failure).

## Reuse without repeating commissioning

Reuse host commissioning and unchanged image/tool qualification when their relevant bytes and inputs are identical. A repository onboarding changes app/source/environment bindings and tests the resulting real application. A CLI/module correction should use the supported stopped-image component update instead of reinstalling Xcode. Host changes, toolchain changes and application changes have different validation scopes.

Run the existing agent inside the selected isolated runtime for exploration and code changes. Rebuild and replay delivered flows independently at exact committed source identities without agent credentials. Optional prose or oversized media produces warnings and must not suppress useful code/evidence delivery; failed assertions remain failed.

Managed credentials and repository environments are supplied per job. No personal session, private key, token or staging value belongs in a sealed image, Git example or public evidence. Future organizations bind their own authority, environments and publication targets; they do not inherit EnviaFlores defaults.

## Commissioning history

[Research snapshot, 2026-09-16](docs/research/2026-09-16/README.md) preserves the reviewed analysis, observed source ownership, failure catalog and Lastmile integration proposal. [Its import manifest](docs/research/2026-09-16/IMPORT-MANIFEST.json) identifies the exact copied documents. Its earlier Codex-only composition proposal is historical; the three-layer composition above records the user's subsequent direction. Historical checkpoint paths in those documents are source references, not files shipped by this repository.

The full private operation archive, raw transcripts and large VM disks are not included here. Large images and private evidence need their own approved artifact storage and verified restore records. A local image alias or a digest without retrievable bytes is not a portable release.
