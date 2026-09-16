# Reusable native iOS runtime: lessons from canary #2343

Analysis date: 2026-09-16. Scope: retained Mac commissioning and canary receipts. This document changes no runtime, account, image, service, source checkout or remote repository. The evidence index below identifies the local originals read for this analysis; it is not permission to publish private logs or infrastructure bindings.

## What was actually achieved

The reusable baseline has a real end-to-end reference execution, not just an image that reports tool versions. Workflow `35059345840` completed `SUCCESS` at `2026-09-16T06:27:16Z`. Exploration ran the authenticated agent, built staging and passed the smoke and generated journey. Independent validation rebuilt clean application commit `382ab9e32f594996c6ed6fbaa92c1ed9bf41bd28` and passed both flows. Both leases were released, both VMs were absent, and owned cleanup was confirmed. [E01–E02]

The resulting flow remains in draft [PR #2367](https://github.com/enviaflores/ef-storefront-ios/pull/2367), SHA-256 `08f7d6a1347f683fce12e6d5c7ef12539f29c7fa4a292beafe6786bb36c5c2e2`. The external publisher verified 17 files, including 13 screenshots, at evidence commit `c6c3553934144b3981236bb5e4c7b1f04cb3a967`; published manifest SHA-256 `05a50cab7126125f4040429b4c7ab094a8a3b262187c89d8657f3588f4df9feb`. Completion is recorded in [issue #2343](https://github.com/enviaflores/ef-storefront-ios/issues/2343#issuecomment-5693038325). These links are references recovered from the local closure; this analysis did not query GitHub. [E01]

The successful native image digest is `93df87c055a2b5043cc37f068da35499115d397238f7f9e9d81ce71480eeb6e0`, with consumer source `3a3e163793d85a2110a7de5098ffe2a2f90b2f3b`. It includes CLI 3.0.2 and the canonical operational-continuation correction. This is an iOS MVP baseline for the accepted staging application. It does not establish Flutter compatibility, a second organization's isolation, generic `test-e2e` routing or fleet-wide production acceptance. [E01, E19]

The video did not reach the published evidence because it exceeded the bounded per-file export size. Optional narrative was also absent. Preserve these limitations: a successful canary does not prove every originally requested artifact was delivered. The exploration review explicitly could not independently establish post-cleanup recovery of the omitted MP4, even though a warning claimed originals were preserved. [E01–E02, E21]

## Where the time went, and what must become reusable

The dominant pattern was a chain of integration defects at different boundaries, discovered one real attempt at a time. Tool installation alone would not have prevented them. Several defects lived outside the image, so another full image build was not the correct response. The following table distinguishes observed failures from the proposed reusable coverage.

| Boundary | Observed failure and correction | Reusable asset or regression to retain |
| --- | --- | --- |
| macOS account admission | Dedicated account had a custom shell incompatible with native account checks, inconsistent Directory Services/service/keychain homes, and no owned keychain bootstrap at normal launchd startup. The SRE source moved to registered `/bin/sh`, one private home and a bounded bootstrap/startup owner. [E04] | Declarative account/home policy and tests using actual Darwin `getusershell`; startup must use the same home and verify the dedicated keychain before spawning the executor. |
| SSH account authorization | Real sshd logged `pam_sacl: denying 'tart-executor' due to failed service ACL check`. The public key was accepted but account authorization failed. Adding only that account to the existing SSH service ACL changed native `pam_acct_mgmt` from 7 to 0, without changing keys or disabling PAM. [E03] | Installer preflight/provisioning for the effective macOS service ACL, plus a signed remote authentication check. Do not confuse key-offer acceptance with successful authentication. At that receipt the installer still lacked this capability: verify its current owner before claiming the gap is productized. |
| Keychain cancellation and receipt semantics | Incomplete/incorrectly typed receipts were accepted; a supervisor could exit during keychain unlock while its detached worker survived. Source correction validated the complete receipt and installed shutdown handling before worker creation, killing/reaping only the owned worker. [E05] | Real signal regression, strict receipt schema, current-supervisor binding and bounded worker cleanup. Preserve unrelated processes. |
| launchd state and recovery | Native `launchctl print-disabled` uses `enabled`/`disabled`; the parser recognized only `false`/`true`. Labels in the override list were also mistaken for loaded jobs. A successful enable step was incorrectly treated as unknown. [E06] | Native output fixtures and a reconciliation operation that executes only the unfinished suffix. Async unload needs a bounded wait, not an immediate assertion followed by repeated bootout. [E08] |
| Image preparation and packaging | A reduced recovery archive omitted transitive imports `tart_execution.py` and `tart_observation.py`. The real installer failed before state mutation. Only the missing files were copied from verified existing source; the recipe was not replayed. [E07] | A generated dependency closure and isolated import test of the *actual distributable archive*, not just repository source imports. Preserve a pristine parent and resumable staged/finalized states. |
| Host/guest transport | A fresh Python child inherited 909 file descriptors, including 906 inheritable sockets, while its soft limit was 256; native subprocess launch returned `EMFILE`. A focused local reproduction established the descriptor problem. The transport needed close-on-exec lifecycle correction. [E08] | Darwin RPC tests covering socket inheritance and child spawn under the real soft limit. Increasing resource limits alone would hide the defect. Do not retroactively attribute an earlier unobserved password failure to this later proven cause. |
| Functional preflight | Tool/version checks could terminate the job before useful real work; correction retained static integrity checks but converted functional preflight failures to truthful warnings, preserving same-binding recovery and session ABI. [E09] | Separate binary/provenance validity from advisory health/version observations. Test warning serialization in the actual hashed session envelope and execute all static checks even after a functional warning. |
| GitHub JIT and bootstrap | The earlier validator did not interpret the actual GitHub JIT form; the canonical pair corrected compatibility and first-error retention. Some historical attempts had already lost their first specific bootstrap diagnostic. [E10] | A sanitized fixture matching the real JIT shape and end-to-end bootstrap contract. Record the first error before cleanup and propagate it separately from a generic runner failure. A later reproduction does not recover lost historical evidence. |
| Application snapshots | A validator rejected supported internal snapshot symlinks as external paths/submodules. The app correction tested the real 1,493-entry snapshot. [E11] | Repository-aware snapshot materialization preserving safe internal links, with explicit policy for external links and submodules. Flutter/CocoaPods layouts must have their own realistic fixtures. |
| Evidence collection | Duplicate references caused the database evidence list to be empty although distinct exported files existed. The corrected collector validates and accounts for every source artifact before deduplicating final references. [E11] | Duplicate-content/path fixtures, durable byte verification and terminal reconciliation. Missing references are not proof that no work happened. |
| Effective staging configuration | The app used `ENV=STAGING` and a bare API hostname; the validator expected lowercase and compared the bare hostname directly with an HTTPS URL. App PR2360 fixed case normalization and comparison of the app's constructed effective URL. No secret or image change was needed. [E12] | Validate the semantics of the *compiled app*, with the application's own URL construction. Preserve multiline configuration bytes. Keep safe match/mismatch receipts so sanitization does not destroy the proof. |
| Agent executable packaging | The pinned Codex binary existed under an archive basename, while the launcher searched for `codex`. Installing the same verified bytes at the intended basename and checking PATH fixed the measured defect. [E13] | Validate executable resolution through the actual nonprivileged launch path; a version pinned in a manifest is insufficient. |
| Agent runtime closure | The real agent then reported missing `codex-code-mode-host`; a single main binary did not provide the required release companion. [E14] | Package the complete supported engine release closure and verify companion resolution. Record exact engine/companion hashes in the reusable image release. |
| Maestro authorization | Tools were enabled, but actual MCP calls were rejected: approval was required while the noninteractive policy was `never`. CLI3.0.1 explicitly approved the four owned bridge tools while preserving sandbox and bounds. [E15] | Noninteractive invocation contract for `inspect_screen`, `take_screenshot`, `run` and `cheat_sheet`; test effective policy, not just tool registration. No new identity or persona is needed. |
| Optional documentation | A real run created a flow after build and Maestro work but failed because `journey.md` was absent. The predicate checked file existence/size, not meaningful content. [E16] | Optional narrative must produce a warning and allow draft code/evidence delivery. Required executable flow and real test results remain independently represented. |
| Time budgets | A 1,800-second agent cap was accidentally applied to the whole validator, including build, agent and tests. The corrected validator uses the image maximum of 7,200 seconds and remaining lease, while retaining the separate agent cap. [E17] | One documented budget model with nested stage deadlines and cleanup reserve. Test boundaries and remaining-time propagation rather than restarting expensive work after an unrelated timer expires. |
| UI state and locale | Later attempts reached the app and failed genuine smoke assertions: startup-modal state, then a product selector on an English catalog while the data/flow expected Spanish. Agent calls also hit observation guards and session deadlines. These were application/session failures, not image-installation failures. [E18–E19] | Fix locale/onboarding state in the repository's simulator recipe; derive selectors from observed UI and preserve discovered replay values with the flow. Distinguish a completed tool call from a passed assertion. |
| Progress reporting | Host database state remained `starting` while the guest runner already executed the job because the host start operation waited for Runner.Listener exit. A parser also undercounted MCP progress when it expected a different event delimiter. [E20–E21] | Stable stage events and structured tool results tied to run/job/generation; use normal exported evidence rather than polling or perturbing the guest. Infrastructure state and application stage must be separate fields. |
| Optional evidence size | The successful exploration emitted `optional-artifact-too-large`; the 25 MiB delivery cap omitted the MP4. [E21] | Define a video encoding/export budget before recording, include thumbnail and explicit omission metadata, and verify retention before deleting a guest. Optional artifact overflow must not suppress valid flow/PR/screenshots/JUnit delivery. |

## Continuation policy that prevents another dead end

The reusable behavior should continue toward useful results after recoverable or optional failures, with a truthful result model. The final canonical correction already permits driver completion and draft/evidence delivery with warnings and `tests_passed: false`; it does not convert failed assertions into passes. The eventual successful run passed its tests. [E19, E01]

Recommended result fields are independent: `execution_completed`, `build_passed`, per-flow test results, `flow_delivered`, `clean_commit_replayed`, `evidence_published`, `cleanup_confirmed`, and `warnings`. This is a proposed normalized interface, not a claim that these exact fields already form one installed schema.

| Event | Continue with what is available | Preserve/report |
| --- | --- | --- |
| Missing prose, optional thumbnail/video, advisory version check | Draft PR, available evidence, remaining applicable validation | Exact warning, omitted artifact/reason, honest coverage |
| Failed smoke or requested assertion | Remaining independent flows where safe; source delivery; repair loop and a new bounded attempt | Original failed JUnit and screenshots; never label it a pass |
| One slow Maestro RPC | Continue waiting for the same in-flight request within the overall budget | Timeout progress/warning; do not resend a UI action whose execution is uncertain |
| Lost authentication, invalid image/source identity, inaccessible staging app | Preserve evidence and deliver an actionable failure; repair the prerequisite | Exact blocker and accountable owner; do not execute the wrong environment or invent success |
| Cleanup outcome uncertain | Reconcile the same owned resources before reusing capacity | Original uncertainty and actual cleanup receipt; do not duplicate a live job |

These are execution semantics, not new human approval gates. Installation/repair actions should continue under the already authorized operation scope. Approval should not be requested per command or per evidence handoff. Duplicate actions with uncertain side effects require reconciliation, not repeated confirmation followed by blind replay.

## What the uxmaltech-collab repository should retain

Store the reusable recipe, release lock, operational runbooks, tested component interfaces and a curated evidence index. Preserve component ownership: shared host/guest fixes already live in templates and are consumed through canonical pins; do not fork those implementations into a second drifting runtime. Large Xcode/macOS disks and private operational logs belong in the appropriate image/artifact store, with immutable digests referenced by the repository. Do not copy the entire root checkpoint tree into Git.

At minimum, retain:

1. One accepted baseline record tying together native image tuple, canonical source/pins, tool/companion hashes, host adapter versions, successful exploration, clean-commit replay, publication and cleanup. Keep failed predecessor references and their resolved regression cases.
2. The supported full-image recipe and the narrow component-derivation procedure. A launcher or Python-module correction should produce a stopped copy-on-write derivative with changed-component provenance, not reinstall Xcode or recreate host identities. [E13, E15, E17, E19]
3. Host commissioning as a reusable owner operation: account and service ACL, one home/keychain context, launchd lifecycle, APFS ownership/quota, dedicated SSH, resource/network bindings and recovery. Organization/repository parameters must not become hard-coded account or image forks.
4. A distributable runtime closure: protected guest driver, session/RPC modules, engine plus companion, hydration package, Java/Maestro/Xcode/Simulator and versioned ABI. Include a tested file list and hashes of the exact installable artifact.
5. Repository adapters for checkout/snapshot, staging configuration, build/install, app identifier/environment assertions, smoke, test discovery and evidence. For Flutter, add the pinned Flutter/Dart SDK and the app's actual iOS dependency/build settings to the macOS image/profile; reuse the same executor, agent, Maestro bridge, replay and publisher.
6. A small failure catalog mapping the table above to regression fixtures and ownership. A runbook should take an operator from the first error to the responsible layer without requiring another full commissioning sequence.

The working environment for iOS is a macOS VM image on Apple hardware. A Linux container can run control-plane components but is not a substitute for the demonstrated native Xcode/Simulator execution. The Flutter extension should be analyzed as an additional toolchain/profile layer; there is no Flutter acceptance receipt in the retained baseline.

## Minimal acceptance and regression reuse

Use the existing successful baseline as evidence for unchanged components. The test plan should be selected by the change, not repeated for every handoff:

| Change | Relevant verification | Evidence to reuse |
| --- | --- | --- |
| New repository on the same image/toolchain | Repository adapter/config validation; one real staging build; observed smoke/journey; independent clean-commit replay; external publication/cleanup | Host installation, SSH/keychain startup, unchanged image/tool hashes and runtime regression receipts |
| Flutter layer added | Exact Flutter release/dependency closure; real iOS build/install from the Flutter repo; accessibility/selector behavior in the compiled app; flow/replay | Accepted host/executor/RPC/agent/Maestro infrastructure where unchanged |
| Driver/CLI/bridge correction | Focused source regression and Darwin import/ABI checks; changed bytes on a stopped derivative; one real affected workflow | Full Xcode installation and unchanged tool/session measurements |
| macOS, Xcode or iOS runtime upgrade | Native startup/session, toolchain/build/simulator and representative real app flows | Unchanged application assertions, publisher and transfer tests where compatible |
| Host/PAM/keychain/launchd change | Native account/service and real dedicated-endpoint verification, shutdown/restart/recovery | App snapshots and image contents where unchanged |
| Publisher-only change | Exact-byte manifest/immutable-link/idempotence tests and publication receipt | Build and flow execution for the unchanged final commit |

Every first organization integration needs a demonstrated identity/environment boundary and a real clean-commit replay. It does not need a new engine persona, per-issue credentials, Xcode image build, permanent runner account or three-day host commissioning. Managed credentials stay outside the sealed image; replay receives only its required repository/staging inputs and no agent credentials.

The successful baseline included 140,000,000,000-byte virtual disk identities and a separate reserve model, not an arbitrary tiny container footprint. Carry measured requirements into release metadata and separately measure the Flutter layer; do not guess additional disk or memory requirements from the native app's values. [E07, E19]

## Work that caused avoidable repetition

These are process conclusions from the receipts, not a claim that all elapsed time was wasted:

- Incomplete installable closures and synthetic interface assumptions moved basic integration detection into expensive real runs. Test the actual packaged import/executable/JIT/MCP contracts first.
- Image, host, app and publisher problems were repeatedly discussed as a single readiness state. Publish stage-specific results and ownership so a validator comparison defect does not lead to another image build.
- Long consolidated handoffs delayed actionable information. Return the first concrete failure, original flow bytes and changed image binding immediately; append the complete evidence index afterward. The final sequence used this successfully. [E21]
- Repeated authorization turns and bounded manual observer wrappers became operational overhead. Preserve the user's authorized scope as a durable record, resume unfinished operations from receipts, and expose ordinary run events through the control plane. Do not introduce new confirmation steps merely to package the historical lessons.
- Finished imports, enables, cleanup and transfers were sometimes at risk of being replayed after a local preparation error. Explicit operation receipts and append-only reconciliation avoided repeating their external effects. Make that resume behavior a normal product feature.
- Drifted parsers and misleading errors obscured facts: `starting` did not mean no guest work; “source changed” could also mean a missing generated flow; sanitized API host was not proof of mismatch; tool completion was not test success. Preserve original result fields and error categories.

## Evidence index

All paths below are relative to `../../checkpoints/` from this document. Digests were recomputed from these exact local originals on 2026-09-16. PR description files E04–E06 record source design and validation at their historical stage; E07 and later physical receipts establish subsequent operations. Local references are not an externally accessible evidence delivery. The future repository should ingest only reviewed nonsecret copies or point to its approved private archive.

| ID | Original | SHA-256 |
| --- | --- | --- |
| E01 | `canary-until-success-20260915/FINAL-CANARY2343-CLOSURE-20260916T0643Z.json` | `d582a8387d9237c83e159ec23f83a5ac76462ad64213fd91d38b3c44f70bb269` |
| E02 | `canary-until-success-20260915/FINAL-CANARY2343-CLOSURE-20260916T0643Z.md` | `5aafed04ae9e370f04b2597bdcedc82ed33b315f3cb4daf9d9fa31ca1c75d95f` |
| E03 | `canary-mvp-20260914/auth-repair-61847/LINUX-HANDOFF.md` | `dbe823ef498a75072316a7f79ce101b0716cd392e1397c2f0da12295ae0abef8` |
| E04 | `native-executor-closure-20260914T015424Z/PR-templates.md` | `cbcd8e380331fc346afc56617baaf4722e804be158e8919b44ccc0b3b66d33db` |
| E05 | `native-executor-closure-20260914T015424Z/keychain-review-corrections/TEMPLATES-PR-BODY.md` | `31fdc4d8cef3334ce0f5236237b8c53c8e2bf7bb5e6ecab368cbeff504e57ebe` |
| E06 | `native-executor-closure-20260914T015424Z/native-launchctl-recovery/TEMPLATES-PR-BODY.md` | `e9584070606238dcab87899398ef212d6c9d9a81c588057832c9a483b3ef90ea` |
| E07 | `native-executor-closure-20260914T015424Z/handoff-finalized92766/LINUX-HANDOFF.md` | `78116dc87f07e09fa6cf6265b37d705e8ed762f95150f9a8e808a5569cc235a5` |
| E08 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T0508Z.md` | `27c9a927e92ff082f27016a02bf71f2c58f96a74b42abd01435a14d21fe31996` |
| E09 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T1209Z.md` | `ff5f6b394f36d8652fb69ac311a3702215401a2a636571a809e00dfaa8d9aa8e` |
| E10 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T1427Z.md` | `617f43fb506063743f208ba0f1edca57c3a00b00932022890abf1d11ecaebc4c` |
| E11 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T1522Z.md` | `5f9dedb90d3a7b4d1b9a4f248605a3bbcdab6e75af33a9845811090a1461fc79` |
| E12 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T1613Z.md` | `f64f732ff05c8b5a81a078d7eea39ecf677533e908fb2e6aab3ff69a20a48cb6` |
| E13 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T1710Z.md` | `ee81f0a37ad183a8e94d34523843067e01823509e343dc6a02cb5ba9d04ffda6` |
| E14 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T1807Z.md` | `e5d0b073155bba1cc4b26b9ee19a9168c411965ddba802c98d44de8a64e770d2` |
| E15 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T2012Z.md` | `b18f29a5bbe7ec80d8974122f5f803f469c9c32b8803e16d31bfbd61fd2e077a` |
| E16 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260915T2240Z.md` | `e2887ad2e3e5c378b4956149f71889dd13a7d28f627d16a7c178b241f47582af` |
| E17 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260916T0240Z.md` | `ffe8df83bf3cd86668208b1aaf91d6bb8e38bb06c89a7e96054e10e21d82cab4` |
| E18 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260916T0445Z.md` | `d95beaef57e0af78d077eb9a088b7113faf4f5cb7fb0eee985514454e915fa75` |
| E19 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260916T0515Z.md` | `5fbf7fdc4495aa07ebca9083e1b92557307b038e683aef802d926285c7c2b3c8` |
| E20 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260916T0543Z.md` | `4ef824802cdbc922e30fb35b0d43edd989f41da451fcc2e5c59a7d1566ba6a69` |
| E21 | `canary-until-success-20260915/ACTIVE-CHECKPOINT-20260916T0615Z.md` | `b96e066ae3699d528df67727932093c088f281af94fd8b06cd673b39e5e819a8` |
