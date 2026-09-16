# AI runner images

Reusable image recipes, compatibility locks and operating knowledge for agents that build and test real applications. The first platform uses this exact composition:

1. **Tart macOS/Xcode/Maestro base**, including iOS Simulator and required platform runtimes such as Java.
2. **One agent-build layer containing Codex, Claude and Grok-build together**, with their complete runtime/companion dependencies.
3. **Flutter/Dart support**, including the pinned iOS toolchain artifacts needed for a small iOS Hello World qualification.

Each layer records its exact parent digest. Engines are installed together in the shared agent layer; authentication is supplied only to authorized jobs and never sealed into any layer.

This repository owns image composition and its qualification records. The existing executor, guest/session/RPC protocol, ordinary resolver and external publisher remain in their canonical owners. A Linux Docker image cannot supply the native Xcode execution environment used here.

## Current status

| Entry | Evidence and limits |
| --- | --- |
| Native macOS/Xcode/Maestro base | Built and sealed. Root builder checks recorded macOS 26.6.2, Xcode 26.5, iOS Simulator 26.5, Maestro 2.10.0 and Java 17. The source image's inventoried consumer/old-agent components were removed; these checks do not claim an application build. |
| Shared Codex + Claude + Grok-build layer | Built and sealed with all three engines together: Codex 0.151.0 and its companion, Claude 2.1.266 and Grok-build 1.0.24. Installation receipts verify exact executable bytes. Nonadministrator launch qualification is tracked separately. |
| Flutter/Dart layer | Built and sealed with Flutter 3.47.4, Dart 3.13.3 and successful iOS precache. The protected SDK seed and writable per-user clone launcher are installed. Hello World build/UI/cleanup qualification remains separate from installation. |
| EnviaFlores native iOS reference | Canary #2343 completed exploration, staging build, Maestro smoke/journey, delivered-flow replay, verified external publication and cleanup. Its image contains the EnviaFlores pack and app-specific driver; it is a historical consumer-specific reference, not the neutral base's direct parent. |
| Lastmile application integration | Source discovery completed for the host app, driver package and direct shared dependencies. The app requests absent driver ref `v0.5.1`; no Lastmile Flutter build is claimed. |

The three stopped Tart layers have these artifact-manifest SHA-256 identities:

```text
retained source 64cdc33e58f67d7cbd8b8a95cc39cb3b7c86e0f56134dbdf8c69b47970c67e0b
  -> native base 0d7cd86cdff86a7f3422c858c4b0da5e1cfc426d01f05864d7b0c09786f080f8
  -> all agents 69d8b384545966a9e88473794dbda2719f9e92a10892735f68a391723eea53d5
  -> Flutter    7a261446e45bce12105c2b6ebb74759c05fa2cd54dc45c663cf34c418ce88c05
```

The [image catalog](catalog/images.json) and [composition record](docs/image-composition.md) distinguish source provenance, installation and qualification. These artifacts are currently local to the Mac; the manifest hashes are not OCI references. No executor admission or production binding change is implied by sealing a layer. The [accepted native reference](provenance/accepted-enviaflores-ios.json) records the historical canary's separate image, app/flow commit and publication evidence.

## Where to start

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

Run the existing agent inside the ephemeral guest for exploration and code changes. Rebuild and replay delivered flows independently at exact committed source identities without agent credentials. Optional prose or oversized media produces warnings and must not suppress useful code/evidence delivery; failed assertions remain failed.

Managed credentials and repository environments are supplied per job. No personal session, private key, token or staging value belongs in a sealed image, Git example or public evidence. Future organizations bind their own authority, environments and publication targets; they do not inherit EnviaFlores defaults.

## Commissioning history

[Research snapshot, 2026-09-16](docs/research/2026-09-16/README.md) preserves the reviewed analysis, observed source ownership, failure catalog and Lastmile integration proposal. [Its import manifest](docs/research/2026-09-16/IMPORT-MANIFEST.json) identifies the exact copied documents. Its earlier Codex-only composition proposal is historical; the three-layer composition above records the user's subsequent direction. Historical checkpoint paths in those documents are source references, not files shipped by this repository.

The full private operation archive, raw transcripts and large VM disks are not included here. Large images and private evidence need their own approved artifact storage and verified restore records. A local image alias or a digest without retrievable bytes is not a portable release.
