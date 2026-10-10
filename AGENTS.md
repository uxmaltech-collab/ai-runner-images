# Working in this repository

Use English for versioned code, comments, documentation and PR descriptions. This repository is the shared home for runner images and toolchains across iOS/macOS, Android, Linux, web and future platforms. It owns reproducible image recipes, tool installation and launch support, compatibility locks, artifact catalogs, qualification fixtures and operating knowledge for all organizations.

For Flutter iOS, the required image order is Tart macOS/Xcode/Maestro base, then one combined agent-build layer with Codex + Claude + Grok-build, then Flutter/Dart support. Other platforms use their native base and compatible tool payloads, retaining all three engines together. Record an explicit immutable parent for each layer. Do not turn the combined agent layer into per-engine variants. Keep authentication outside sealed images.

## Ownership and scope

- Reuse canonical executor, host installer, guest/session/RPC and resolver components from their existing owners. Do not copy checkpoint repair scripts into a second production implementation.
- Register new platform and tool support here. Scope declarations are plans until recipes, artifacts and actual qualification exist; never label an Android or Linux image validated using iOS evidence.
- Keep application flows and business code in their owning application/package repositories. Neutral fixtures here qualify the image mechanics; they do not establish a customer's staging acceptance.
- Keep host-specific identities, storage, endpoint and network bindings in the host owner's declaration, including APFS/keychain settings where macOS requires them. Never assume a personal shell environment is the executor's environment.
- Preserve unrelated accounts, services, VMs, builders, original image tuples, worktrees and receipts.

## Development and production adoption

Follow [autonomous native development](docs/native-development.md) for an image,
feature or mechanical-canary repair. The native owner executes and fixes the
whole applicable mechanical path in a disposable clone; it does not wait for
another host to report each next failure. Use production adoption for an already
qualified generation, preserving admission control, active jobs and recovery.
An image/tool check is not current-runtime execution or GitHub delivery. Use
the selected release's real entrypoints and report unsupported stages honestly.
Instruction-only changes do not trigger runtime releases, image builds or
application pin churn. Keep one publication owner and reuse existing approval.

## Evidence and execution

- Inspect recipes, locks and completed receipts before preparing replacements. Resume only unfinished steps after reconciling uncertain results; do not blindly repeat publication, VM lifecycle, UI actions or cleanup.
- Continue work within the user's existing authorized scope. Stage bookkeeping and per-command execution do not create new approval requirements.
- Promote shared runtime code through its owner's canonical source/pin process. Application candidate commits may be tested as candidates without promoting an open infrastructure branch into the runtime.
- Record exact source commits, dependency closure, tool builds/hashes, image identities, actual test results and owned cleanup. Distinguish plans, isolated tests, image admission and real application execution.
- Select regressions by the changed surface. Reuse valid evidence for unchanged inputs; do not repeat full suites for documentation edits, transfers or handoffs.
- Preserve failures and partial evidence. Optional narrative/media problems become explicit warnings; do not turn failed assertions into passed results or claim a different commit was tested.
- Qualify each image in its intended unprivileged execution context. For GUI applications, build and interact with the real app in that guest/session or emulator/browser context. Independent replay reconstructs exact committed inputs in a clean execution and excludes agent credentials.

After three failed attempts at the same operation, research the first error,
actual inputs and current primary sources before another execution. Carry the
count across releases, hosts and sessions; retries require a justified changed
approach and remain within existing authority. See
[the research and operational decisions](docs/github-runner-research.md).

## Secrets and artifacts

- Never commit secrets, private keys, authentication sessions, raw private transcripts or customer configuration values. Use managed references and sanitized verification results.
- Do not embed job credentials or repository source caches in a shared sealed image. Keep organization-specific material scoped to its derivative or ephemeral job.
- Keep VM disks and large tool payloads in approved artifact storage; commit their immutable identities, provenance and verified restoration procedure.
- Preserve native image, OCI manifest, disk/config/NVRAM and source-commit identities as distinct fields. Never invent unavailable pins, digests or qualification results.

## Coordination

Use the declared owner for each source/runtime surface and avoid concurrent edits to shared branches. Keep GitHub calls grouped and sequential; do not poll CI or dispatch duplicate jobs to discover state that receipts already establish. Do not create `CODEOWNERS` entries without assigned maintainers.

## Image construction entrypoint

Promote reusable image-building Python into `scripts/build-images.py` and its
fixed platform backends, documented in `docs/build-images.md`. Checkpoint scripts
are historical evidence, not build dependencies. Keep the source commit, pinned
parent, local artifact and qualification results distinct. Local Mac images are
permitted; remote publication is not a prerequisite for source reconstruction.

## Organization-agnostic source of truth

This runner-image repository is a source of truth shared by every organization that adopts it. Its versioned content, its issues and its pull requests know no organization: no organization name, host name, account identifier, cloud region, repository name, environment-variable name, nor a cloud or vendor product used as a concept of the design. Examples use placeholders such as `<organization>/<repository>`, `<host>`, `<listener-id>` or `__PLACEHOLDER__`. An organization's facts live in that organization's own repositories (its canon declarations, its resource packs, its infrastructure) and reach this code only through declarations and configuration read at runtime. A change that needs an organization's fact to make sense belongs in that organization's repository, not here. Product names of harnesses and tools (Codex, Claude Code, Grok Build, GitHub) are allowed where the code or document is about that product.
