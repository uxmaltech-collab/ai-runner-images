# Reusable iOS agent runtime: repository proposal

Analysis date: 2026-09-16. Status: design and implementation proposal, grounded in the completed EnviaFlores iOS MVP. Proposed repository: **`uxmaltech-collab/ai-runner-images`**, initially private. This directory is a reviewable documentation package; proposed interfaces are not installed runtime contracts.

The objective is to make the next iOS application an onboarding task instead of repeating host commissioning, image repair, agent integration and evidence publication. Store the recipes, compatibility locks, operating procedures, failure regressions and acceptance records needed to reproduce and maintain the result.

## What is already proven

The reference is [canary #2343](https://github.com/enviaflores/ef-storefront-ios/issues/2343#issuecomment-5693038325), workflow [35059345840](https://github.com/enviaflores/ef-storefront-ios/actions/runs/35059345840), completed successfully at 2026-09-16T06:27:16Z:

- Codex executed in the macOS guest using managed authentication, built staging, inspected the real application with Maestro and generated a flow.
- Smoke and journey passed. A second independent guest rebuilt clean commit `382ab9e32f594996c6ed6fbaa92c1ed9bf41bd28` and passed both flows without requiring agent credentials.
- The flow was delivered in [draft PR2367](https://github.com/enviaflores/ef-storefront-ios/pull/2367). Both native leases and simulators were cleaned up.
- The external publisher verified 17 files, including 13 screenshots, at evidence commit `c6c3553934144b3981236bb5e4c7b1f04cb3a967`.
- The oversized video and absent optional narrative remain recorded limitations. Earlier failures remain failures in the historical record.

This proves one native iOS integration. It does not yet prove a Flutter image, an independent `test-e2e` command, native execution of ordinary `resolve`, or isolation and onboarding across multiple organizations.

## Recommendation

Create a neutral repository for **image composition and its operational knowledge**. Continue consuming the executor, guest protocol, ordinary agent hydration and shared control-plane machinery from their existing owners. The repository must not become a fork of the resolver or a second control plane.

The deployable iOS artifact is a **macOS/Tart virtual-machine image** with Xcode and Simulator. Linux containers continue to host orchestration and publication. Tart supports OCI image registries; Flutter's iOS development setup uses Xcode and iOS platform support. See [Tart](https://tart.run/) and [Flutter iOS setup](https://docs.flutter.dev/platform-integration/ios/setup).

Use three compositions:

1. A neutral macOS toolchain base: Xcode, Simulator, Java/Maestro, Python, Git, Node, Codex and its required companion executables.
2. A Flutter iOS capability derivative: pinned Flutter/Dart, cached engine artifacts and the project's supported native dependency tooling.
3. A consumer/profile derivative: exact organization resource-pack closure, protected driver and declarative repository bindings. Credentials are hydrated per job, never sealed into an image.

The accepted `93df87…` image remains a reference and fallback for EnviaFlores. It contains the EnviaFlores pack and a repository-specific driver, so it is not already an organization-neutral base.

## Important gaps discovered in code

| Gap | Consequence | Required change |
| --- | --- | --- |
| `journey_jobs.driver()` explicitly accepts only `enviaflores/ef-storefront-ios` and its profile | A new repository declaration alone cannot run | Parameterize trusted repository/profile contracts in the owning source and consume the canonical release |
| Image composition fixes the EnviaFlores pack and `storefront-ios` entry | Renaming the final image does not generalize it | Separate reusable toolchain composition from consumer-specific pack composition |
| Native tool declarations use an exact tool-key set | Adding a `flutter` JSON entry is insufficient | Extend the shared tool/capability validation and real guest probes |
| Ordinary `resolve`/`review` still use the Linux profile | A successful journey does not establish native resolver builds | Adopt command-to-profile routing for native resolver work explicitly |
| No literal `test-e2e` implementation found in the inspected canonical pack | Existing replay is not automatically a standalone command | Add authenticated existing-flow execution without inventing an exploration predecessor |
| App validator assumes the current app's build and environment conventions | A Flutter flavor may keep its effective API configuration in Dart | Introduce a build/environment adapter and verify the resulting app's effective configuration |
| The successful SSH repair required a macOS service-ACL membership change still absent from the canonical installer | A fresh Mac can reproduce the authentication failure despite a valid SSH key | Productize SACL prerequisite/reconciliation in the template-owned host installer |
| The consumer-owned ordinary CLI contains an EnviaFlores pack-origin check | A templates pin change alone does not onboard another organization | Parameterize that CLI contract in its owner and qualify a second pack |

## What the repository stores

- Versioned native recipes and complete dependency/compatibility locks.
- A registry of accepted image digests, source commits and qualification records.
- Contracts and examples for consumer profiles and app-owned adapters.
- The recovered lessons, diagnosis recipes and regression fixtures for every material commissioning failure.
- A sanitized reference-case ledger connecting issues, PRs, commits, images, JUnit, publication and cleanup receipts.
- Runbooks for one-time host commissioning, image composition/update, repository onboarding, recovery and evidence export.

Large VM disks belong in a private image/artifact store, with exact digests and verified restoration procedures. Raw transcripts, credentials and host-private declarations do not belong in Git. A local pathname alone is not a recoverable archive reference. The proposal therefore includes an archive-transfer work item before the history is declared fully preserved outside this Mac.

## Documents

- [Architecture and owner boundaries](ARCHITECTURE.md)
- [Flutter adapter and command gaps](FLUTTER-ADAPTER.md)
- [Selected first Flutter acceptance: Last Mile](LASTMILE-FIRST-ACCEPTANCE.md)
- [App/package source tuple and independent replay](LASTMILE-CROSS-REPO.md)
- [Existing Last Mile resource-pack gaps](LASTMILE-PACK-AUDIT.md)
- [Repository layout and onboarding contract](REPOSITORY-BLUEPRINT.md)
- [Implementation sequence and acceptance](IMPLEMENTATION-PLAN.md)
- [Recovered lessons and failures](LESSONS-AND-FAILURES.md)
- [Observed baseline and source ownership](OWNERSHIP-AND-BASELINE.md)
- [Accepted reference case](provenance/accepted-canary.json)
- [External references](SOURCES.md)

## Repository choice and next step

One grouped GitHub read found 22 repositories in `uxmaltech-collab`. `ai-runner-images` was not present. `studio-github-runners` exists but had no default branch; it is a possible alternative only after assigning it this shared role. `agent-runtime` describes a separate Collab agent runtime, and `ai-templates-resources` already owns shared execution infrastructure. The neutral name avoids making all future organizations appear to depend on Studio.

The first implementation slice is a reproducible catalog of the proven native baseline and its history, followed by the Flutter tool/adapter extension and a real Flutter qualification. The user selected `enviaflores/ef-lastmile-flutter` as the host app and `enviaflores/lastmile-drivers-pkg-flutter` as its driver package. Both consume private packages from `enviaflores/shared-package-flutter`. This is now the first concrete acceptance case; a neutral fixture is only an auxiliary mechanism check.

The follow-up source review found a missing requested driver ref (`v0.5.1`), no committed Pub lock or exact SDK pin, and a `Runner` build configured through Dart defines rather than an observed staging flavor. The owning source/profile changes and managed environment requirements are recorded in [the Last Mile acceptance analysis](LASTMILE-FIRST-ACCEPTANCE.md). No Flutter build or source repair is claimed.
