# Runner platforms and tools

`uxmaltech-collab/ai-runner-images` is the common home for all runner images and toolchains: iOS/macOS, Android, Linux, web and future platforms. Organization and repository profiles consume these artifacts for the existing resolver, journey creation, end-to-end testing and other jobs. Adding an organization binds its application sources, managed accounts, environment and evidence policy; it does not require another copy of the image repository.

## What belongs here

| Area | Repository content |
| --- | --- |
| Platform images | Build recipes and composition operations for compatible native VM and container artifacts |
| Runner tools | Pinned install sources, payload verification, image-local launchers, dependencies and writable cache policy |
| Agents | Codex, Claude and Grok-build installed together with target-compatible binaries and their complete dependency closure |
| Framework capabilities | Flutter/Dart, Android tooling, browser/Playwright tooling and future language or test capabilities |
| Artifact registration | OS/architecture, immutable parents, source commits, component hashes, distribution locations and restore verification |
| Qualification | Representative real builds and tests, CLI launches, screenshots/JUnit where applicable, logs and owned cleanup |
| Operating knowledge | Recovery procedures, reusable commissioning evidence, failed attempts and compatibility findings |

Upstream tool implementations retain their own source owners. This repository owns their packaging and composition into runner environments. Shared executor, resolver/hydration, credentials, scheduling and publisher protocols keep their [existing owners](ownership.md); this scope does not create replacement runtime services.

## Composition by platform

The shared pattern is **platform base → combined agent-build layer → optional framework capabilities**. All three agent engines are present together. Each recipe selects payloads built for its actual OS and architecture; a macOS lock must not be reused as a Linux binary lock.

For iOS, the required base is **Tart macOS/Xcode/Simulator/Maestro**, followed by **Codex + Claude + Grok-build**, then **Flutter/Dart** when requested. This is the first qualified implementation. It uses a native VM image and Apple tooling.

Android recipes will compose a compatible Linux execution environment, Android SDK/emulator, Java and Maestro, plus the combined agents and optional framework support. They must declare and qualify their emulator acceleration, device isolation and cleanup requirements on the intended executor.

Linux recipes will supply reusable Linux runner bases, combined agents, build toolchains and job utilities. Browser/Playwright support is a capability of those Linux artifacts. A Linux host's existing control-plane installation is separate from these job execution images.

Android, Linux and web entries currently declare scope only. This repository has not built or qualified their images. The iOS result cannot be substituted for their platform-specific build, launch, UI or cleanup evidence.

## Repository layout and registration

- `recipes/` holds platform and tool recipes, pins and launch support. Existing qualified paths remain stable; add new platform-specific recipes alongside them.
- `catalog/platforms.json` declares platform scope and links only demonstrated qualifications.
- `catalog/images.json` registers actual image identities and their evidence. Its current logical layer list describes the first Flutter iOS profile; future profiles must carry their own explicit composition.
- `fixtures/` contains neutral qualification applications and tests. Application journeys remain in the consuming app repository.
- `qualification/` and `provenance/` retain measured results, source closure and artifact lineage.
- `docs/` records architecture, ownership and recovery. Historical research remains labeled with its original scope and date.

Register a tool's install source, version, OS/architecture, byte hashes, dependency closure, installation/launch commands and unprivileged runtime requirements with its recipe. Register a release only from measured artifact identities and completed qualification receipts. Consumer command support must identify its tested profile and source; tool presence alone does not prove workflow integration.

Image management belongs here, while large image bytes and tool archives use appropriate artifact storage. Git holds recipes, metadata and reviewable evidence; native Tart tuple identities and OCI distribution digests remain distinct. Record the real storage location and verified restoration result rather than an invented registry reference. The current qualified iOS image remains local to mac-ultra.

Authentication and repository environments are delivered to authorized jobs through existing managed mechanisms. Shared images contain public tools and required runtime components, with no organization credentials, personal sessions or customer source caches sealed into them.
