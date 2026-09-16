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
| EnviaFlores native iOS reference | Canary #2343 completed exploration, staging build, Maestro smoke/journey, delivered-flow replay, verified external publication and cleanup. Its image contains the EnviaFlores pack and app-specific driver; it is consumer-specific and its known distribution is local to the Mac. |
| Shared Codex + Claude + Grok-build layer | Planned until exact installation identities and actual launch results for all three engines are recorded. |
| Flutter/Dart / iOS Hello World | Planned until its exact shared-agent parent, resulting image identity and actual build/UI/cleanup receipts are recorded. Source documentation or an example manifest is not runtime acceptance. |
| Lastmile application integration | Source discovery completed for the host app, driver package and direct shared dependencies. The app requests absent driver ref `v0.5.1`; no Lastmile Flutter build is claimed. |

The [image catalog](catalog/images.json) records these states independently. The [accepted native reference](provenance/accepted-enviaflores-ios.json) records the exact successful image, app/flow commit, tool versions and publication evidence. Catalog metadata does not replace native image admission.

## Where to start

1. Read [architecture](docs/architecture.md) and [ownership](docs/ownership.md) before changing an image or shared component.
2. Select a recipe and its exact compatibility lock. Use its documented owner operations; preserve the accepted parent and create a distinct derivative.
3. Record real qualification results under `qualification/`. Update the catalog only from completed receipts, preserving failed attempts and limitations.
4. Use [recovery](docs/recovery.md) to reconcile interrupted work and execute only unfinished operations.

Recipe, fixture, lock and qualification implementations live in `recipes/`, `fixtures/`, `locks/` and `qualification/` as they are added. This README does not claim that a directory name is a functioning builder or prescribe commands that have not been implemented.

## Reuse without repeating commissioning

Reuse host commissioning and unchanged image/tool qualification when their relevant bytes and inputs are identical. A repository onboarding changes app/source/environment bindings and tests the resulting real application. A CLI/module correction should use the supported stopped-image component update instead of reinstalling Xcode. Host changes, toolchain changes and application changes have different validation scopes.

Run the existing agent inside the ephemeral guest for exploration and code changes. Rebuild and replay delivered flows independently at exact committed source identities without agent credentials. Optional prose or oversized media produces warnings and must not suppress useful code/evidence delivery; failed assertions remain failed.

Managed credentials and repository environments are supplied per job. No personal session, private key, token or staging value belongs in a sealed image, Git example or public evidence. Future organizations bind their own authority, environments and publication targets; they do not inherit EnviaFlores defaults.

## Commissioning history

[Research snapshot, 2026-09-16](docs/research/2026-09-16/README.md) preserves the reviewed analysis, observed source ownership, failure catalog and Lastmile integration proposal. [Its import manifest](docs/research/2026-09-16/IMPORT-MANIFEST.json) identifies the exact copied documents. Its earlier Codex-only composition proposal is historical; the three-layer composition above records the user's subsequent direction. Historical checkpoint paths in those documents are source references, not files shipped by this repository.

The full private operation archive, raw transcripts and large VM disks are not included here. Large images and private evidence need their own approved artifact storage and verified restore records. A local image alias or a digest without retrievable bytes is not a portable release.
