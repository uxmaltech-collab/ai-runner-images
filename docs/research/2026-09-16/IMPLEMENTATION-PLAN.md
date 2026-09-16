# Implementation sequence and acceptance

This is an actionable proposed backlog. No runtime change, repository creation or Flutter qualification is claimed by the analysis. Existing canary acceptance and its original failures are preserved.

| Slice | Deliverable and owner | Done when |
| --- | --- | --- |
| 1. Preserve the proven baseline | `ai-runner-images`: charter, ownership, recipe inventory, source/receipt map, reference case and private archive index | Another operator can retrieve the accepted source/receipt package and verify its manifest without access to the original root home |
| 2. Productize completed host repairs | Templates owner: add the verified missing macOS service-ACL prerequisite/reconciliation and retain the shell/HOME/keychain/recovery fixes | A fresh host/account installation reaches the same real SSH/service context through owner operations, without undocumented manual edits |
| 3. Generalize existing interfaces | Consumer owners and shared templates/CLI: replace app-specific origin/profile/publisher assumptions with trusted declarations | Two distinct organization/repository fixtures exercise binding and routing without introducing a second agent or control plane |
| 4. Compose a neutral toolchain base | Image repository plus existing native installer | Complete runtime/tool closure, real intended GUI session, shutdown/restart and image finalization are reproducible; prior reference remains available |
| 5. Add Flutter capability | Shared tool schema/probes and image recipe | Pinned Flutter/Dart/dependency closure runs as the job user; a real Flutter simulator app builds and exposes UI to Maestro |
| 6. Adopt application adapter and commands | App repository plus command/driver owner | Native `resolve` routing is explicit; `create-journey` passes; standalone `test-e2e` executes existing committed flows without an agent or fictitious predecessor |
| 7. Publish and qualify the reusable release | Image repository, registry owner and consumer control plane | Distribution is retrievable and byte-verified; first real Flutter app passes independent replay, external evidence and cleanup |
| 8. Onboard a second organization | Its resource pack and app owners | Same shared mechanics work with different authority/environment/publication bindings and no repeated host setup |

Slices 1–3 can be prepared while the first Flutter app's environment is being supplied. Compatible source changes should be grouped by owner and compatibility boundary. Preserve canonical post-merge promotion; do not patch open-PR files into a sealed runtime to save a round trip.

## First repository change set

Create the repository charter and structure from the blueprint; add this analysis, the accepted native reference, source/compatibility inventory and regression catalog. Add real recipes only after they call the supported operations and their source ownership is resolved. Never label a skeleton or example manifest as a working builder.

Prepare a private portable archive of reviewed original receipts and the existing source deliveries; keep large images separate. Verify all manifest entries after retrieving that archive through the destination available to the next operator. The current analysis package includes a portable nonsecret acceptance summary and local evidence index, not the entire private operational archive.

The ordinary CLI's pack-origin hardcoding is consumer-owned in the inspected source. Its generalization needs its own source change/release or deliberate upstream extraction; a templates pin bump alone cannot fix it. The shared image reference parser already supports generic repositories, so it does not need to be weakened or rewritten for this migration.

Add an explicit restore procedure: recover source at exact commits, retrieve offline dependencies/image by digest, verify all bytes, reconcile the existing host/image state, then execute only missing steps. A rebuild should not depend on terminal history, implicit PATH, a personal login session or unexplained files remaining in a builder.

## Regression selection

| Changed surface | Required evidence | Reuse |
| --- | --- | --- |
| Docs/catalog with unchanged runtime | Schema/reference/digest consistency | All unchanged physical execution receipts |
| New app binding | App adapter/config/source contract and one real build/flow/replay chain | Host installation, SSH/keychain, unchanged toolchain qualification |
| Flutter layer | Native SDK/plugin builds, semantics inspection, controlled actions and replay | Unchanged executor/RPC/agent/publisher behavior |
| CLI/driver/bridge | Focused functional tests, actual distributable import/companion closure, affected real path | Xcode installation and unchanged image tools |
| Host installer/session/OS | Native account/PAM/keychain/startup/recovery and guest context | Unchanged app assertions and publisher tests |
| Publisher/export | Manifest/digest, sanitization, retention, immutable readback and idempotency cases | Already valid build/flow results for the exact same commit |

Historical regression fixtures must cover real JIT shape, Darwin launchctl strings, restricted-account PAM service ACL, HOME/keychain consistency, transitive Python imports, child descriptor inheritance, Codex companion resolution, noninteractive MCP permission, preserved CR/LF configuration, environment normalization, safe snapshot symlinks, nested time budgets, optional narrative/media, duplicate evidence content and uncertain publication reconciliation.

Reuse passing evidence only for identical relevant bytes and inputs. Do not repeat a full suite for a transfer, PR body edit or ownership handoff. Do not use passing shim tests to claim native installation, Flutter build or UI execution.

## Operation model

Prepare all compatible inputs, preconditions, commands, effects, recovery and receipt locations as one operation plan. Resume from completed receipts under its existing authorization. Stage transitions are operational bookkeeping, not a request for a new code per command.

Persist stage progress through the existing control plane: queue, guest/session, checkout, configuration, build, agent, individual flows, code delivery, replay, publication and cleanup. The first meaningful error should be available immediately, before a large archive is assembled. Distinguish an executor lifecycle state such as `starting` from the actual in-guest application stage.

Image/component changes must retain a pristine parent and update only the intended derivative. Generalize the verified stopped-image component-update procedure in its owner so future launcher/CLI fixes do not reinstall Xcode. Record old and new component digests and the resulting full image identity.

## Concrete remaining inputs

- First Flutter repositories are selected: `ef-lastmile-flutter` plus `lastmile-drivers-pkg-flutter`, with `shared-package-flutter` dependencies. Reconcile the unresolved `v0.5.1` driver ref, capture portable dependency locks, select an exact compatible SDK and bind the Last Mile managed environment. See [the concrete acceptance plan](LASTMILE-FIRST-ACCEPTANCE.md). This does not change the shared-agent design.
- Proposed repository name/charter implementation decision: neutral `ai-runner-images` recommended; existing empty `studio-github-runners` is an alternative.
- Approved image/artifact registry location, access owner and retention for recoverable images/archives. Do not equate a local Tart alias with an existing registry publication.
- Missing exact reusable-lock values for guest macOS and Tart, recovered from existing provenance or measured during the authorized image work.
- Each new organization's GitHub/OIDC/publisher and managed environment/account references. No secret values in chat or Git.

No new staging data request is needed for the already accepted EnviaFlores case. Flutter SDK/version choices and additional host capacity have not been invented. The observed final native jobs used 4 CPU, 8192 MiB RAM and a 140 GB disk request; this is a reference measurement, not a universal Flutter requirement.

## Completion definition

The initial repository implementation is complete when it contains usable recipes, exact source/dependency locks, recoverable artifacts and a documented owner-driven rebuild/update procedure. The Flutter release is accepted only after a real Flutter app passes native build, effective staging verification, observed Maestro journey creation, delivered-flow replay, immutable publication and cleanup. Multi-organization support is accepted by a second independently bound organization, not by adding another example YAML file.

This design should remove repeated commissioning work. It does not promise a universal onboarding duration: app-specific build dependencies, staging availability and UI behavior still need real validation.
