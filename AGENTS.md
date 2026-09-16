# Working in this repository

Use English for versioned code, comments, documentation and PR descriptions. Keep this repository focused on reproducible image composition, compatibility locks, qualification fixtures and operating knowledge.

The requested image order is Tart macOS/Xcode/Maestro base, then one combined agent-build layer with Codex + Claude + Grok-build, then Flutter/Dart support. Record an explicit immutable parent for each layer. Do not turn the combined agent layer into per-engine variants. Keep authentication outside sealed images.

## Ownership and scope

- Reuse canonical executor, host installer, guest/session/RPC and resolver components from their existing owners. Do not copy checkpoint repair scripts into a second production implementation.
- Keep application flows and business code in their owning application/package repositories. Neutral fixtures here qualify the image mechanics; they do not establish a customer's staging acceptance.
- Keep host-specific account, APFS, endpoint, keychain and network bindings in the host owner's declaration. Never assume a personal shell environment is the executor's environment.
- Preserve unrelated accounts, services, VMs, builders, original image tuples, worktrees and receipts.

## Evidence and execution

- Inspect recipes, locks and completed receipts before preparing replacements. Resume only unfinished steps after reconciling uncertain results; do not blindly repeat publication, VM lifecycle, UI actions or cleanup.
- Continue work within the user's existing authorized scope. Stage bookkeeping and per-command execution do not create new approval requirements.
- Promote shared runtime code through its owner's canonical source/pin process. Application candidate commits may be tested as candidates without promoting an open infrastructure branch into the runtime.
- Record exact source commits, dependency closure, tool builds/hashes, image identities, actual test results and owned cleanup. Distinguish plans, isolated tests, image admission and real application execution.
- Select regressions by the changed surface. Reuse valid evidence for unchanged inputs; do not repeat full suites for documentation edits, transfers or handoffs.
- Preserve failures and partial evidence. Optional narrative/media problems become explicit warnings; do not turn failed assertions into passed results or claim a different commit was tested.
- Build and interact with the app in the intended nonadministrator guest/session. Independent replay reconstructs exact committed inputs in a clean execution and excludes agent credentials.

## Secrets and artifacts

- Never commit secrets, private keys, authentication sessions, raw private transcripts or customer configuration values. Use managed references and sanitized verification results.
- Do not embed job credentials or repository source caches in a shared sealed image. Keep organization-specific material scoped to its derivative or ephemeral job.
- Keep VM disks and large tool payloads in approved artifact storage; commit their immutable identities, provenance and verified restoration procedure.
- Preserve native image, OCI manifest, disk/config/NVRAM and source-commit identities as distinct fields. Never invent unavailable pins, digests or qualification results.

## Coordination

Use the declared owner for each source/runtime surface and avoid concurrent edits to shared branches. Keep GitHub calls grouped and sequential; do not poll CI or dispatch duplicate jobs to discover state that receipts already establish. Do not create `CODEOWNERS` entries without assigned maintainers.
