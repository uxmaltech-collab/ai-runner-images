# Lastmile application and driver-package source contract

Status: proposed extension to the reusable Flutter iOS design, 2026-09-16. This document performs no checkout, build, source edit, publication or runtime change. Its field names and routing rules are a design, not an implemented command contract.

## Relationship established by the user

The first Flutter targets are:

- `enviaflores/ef-lastmile-flutter`: the integrating application.
- `enviaflores/lastmile-drivers-pkg-flutter`: the driver package mounted into that application.

This establishes the application's role as the real UI execution target and the package's role as an application dependency. The source observations below now establish part of their integration contract; the proposed runtime interfaces remain unimplemented. An independently runnable package example is not established and would not replace acceptance in the integrating app.

The existing EnviaFlores native iOS canary remains evidence for the infrastructure mechanics. It is not a Flutter build or Lastmile acceptance receipt. A Flutter-capable image/profile can serve both repositories through the existing resolver; another persona or permanent runner is unnecessary.

## Source facts recovered for this analysis

Root supplied grouped repository reads, retained under `discovery-lastmile/`. This amendment read those local extracts only and made no network call.

| Observed snapshot | Exact source identity |
| --- | --- |
| Application main | Commit `f2a58df8629a89f1c87bb285b62b1f03d45709b3`; tree `335311d2ad1bae538a7f899520603caeaba998ad` |
| Driver-package main | Commit `89cdefeaadce51f282aac9c50d9b0ab0cbdb0c58`; tree `783f38b093d925321b9dcf0254e60cd297542724` |

The application declares Dart `^3.12.2`, Flutter `>=3.44.0`, and dependency name `lastmile_drivers_pkg_flutter` as a Git dependency at `git@github.com:enviaflores/lastmile_drivers_pkg_flutter.git`, ref `v0.5.1`. The manifest's underscore spelling resolves to the same canonical repository as the user's hyphen spelling, GitHub repository ID `R_kgDOTa9Pgw`, confirmed in root's third grouped read. The observed package main declares Dart `^3.12.2` and Flutter `>=3.35.0`.

**The application's requested dependency is currently unresolved.** At `2026-09-16T16:54Z`, both `refs/tags/v0.5.1` and `refs/heads/v0.5.1` returned null. The complete six-tag listing ended at `v0.5.0`, peeled commit `25638948fbd69f9696206e808baa8c35397a8c4b`. No build or `pub get` was attempted for this analysis; this is a source/ref discovery defect, not a claimed runtime failure. Do not silently fall back to `v0.5.0` or package main. The owners must select the intended immutable package revision and correct the app dependency, or publish the intended package release through its normal owner. Only then can a compiled tuple be established. Package main is an observed development snapshot, not the application's resolved dependency.

Both manifests also reference `enviaflores/shared-package-flutter`, with multiple package-relative paths and package-specific tag refs. Root resolved all 18 unique directly declared shared tag refs in the third read; that is not a resolved full transitive graph. Consequently the reproducible input is an app/package pair **plus the complete dependency closure**, including this third repository and the actual commit behind each selected tag. Do not collapse all shared packages to one arbitrary repository head: distinct refs may select distinct commits. Preserve the effective graph and reconcile shared dependency constraints. Different development-only refs are not, by themselves, proof of an app runtime conflict.

Root's scoped source read found no `pubspec.lock` in either snapshot and no FVM configuration. An iOS `Podfile.lock` was recovered for the app, but it does not lock Dart/Git resolution. The first successful dependency resolution therefore needs a retained exact lock/graph and approved reproducible representation for replay; a Git tag alone and a broad SDK constraint are not complete immutable locks. Do not choose a concrete Flutter release solely from either minimum; qualify a pinned release satisfying the app and the actual consumed dependency constraints.

The app README documents private `.env.json` supplied through `--dart-define-from-file`, including `DRIVERS_BASE_URL` and `ENVIRONMENT`, plus Firebase development inputs. Root found only the shared `Runner` scheme and no declared flavor scheme in the inspected source; do not invent a `staging` flavor to replace the observed Dart-define mechanism. Native iOS Maps configuration is separate: `MAPS_API_KEY_IOS` in `ios/Flutter/Secrets.xcconfig`. The documentation explains that a missing optional xcconfig may still permit compilation while leaving a nonfunctional map. A successful build is therefore insufficient evidence of correct runtime configuration. These are observed configuration *references and mechanisms*, not delivered secret values or approved Lastmile staging endpoints. Do not reuse the storefront staging API by default.

The package's consuming contract owns driver login/session and the two-step phone/SMS/code UI. Its base URL uses `DRIVERS_BASE_URL`, with a documented `LAST_MILE_BASE_URL` fallback. The app mounts this domain and supplies app/platform integration. Real journey planning must account for this login state using approved managed staging/test-identity capabilities; no OTP bypass or account credential is invented by this proposal.

Local extract digests: `app/pubspec.yaml` → `32889caf60f8dd26bdd4cd27f540193b81d483362dd110056be1f98ce5df0ce1`; `package/pubspec.yaml` → `29a59574b1791c83bd1526550f6bf2a6cbaba74bdfbd54224fc8322f45860eb5`; `app/README.md` → `95d42d163cb21b98b01819aa921f42f39d90a8b1f5c8dc01dd8e417a4462ab84`; `package/docs/consuming-the-package.md` → `eca5f09f99f11a2c4dd2076517011b79487c645a9e59e66d2850273f7c980f6e`. Discovery receipts: `receipt-01.json` → `7d9ec89792fde0c4ec4e43524df2ef9d2e625a2fed9f6f50c21e2bc7f57c60f7`; `receipt-02.json` → `459ef0f54bdb853c600f57cc4d19e7ef73075a9f0f19444bc646e3cdcac727a5`; `receipt-03.json` → `c5cfa57f63c93ecfd53a101ada1573691330ec41d54d61fd5aa3bf1e2c38305a`. Third response with repository/ref identities and direct shared-ref mapping: `response-03.json` → `4ccf6c73d3f0e8b49719a72445fcc9e831666d76f74db2cf9fc86b8003139c90`.

## One reproducible input tuple across two repositories

Pin the application and package together before compilation, and freeze the fully resolved dependency closure. The identity being tested is the pair of exact source snapshots plus the declared way they are connected and their resolved dependencies, not just the application commit or package PR number.

The tuple should contain the following proposed fields:

| Field group | Contents |
| --- | --- |
| Application | Repository identity, full commit, tree identity, app root and relevant manifest/lockfile digests |
| Driver package | Repository identity, full commit, tree identity, package root and relevant manifest/lockfile digests |
| Integration | Source-derived package name and dependency mechanism; versioned binding/materialization recipe; actual resolved package identity; resulting lockfile/dependency graph digest |
| Dependency closure | Every selected Git repository/ref/peeled commit/package subpath and immutable hosted dependency identity, including `shared-package-flutter`; exact effective lock/graph used by the build |
| Runtime | Accepted image/native manifest identity, source-pack/driver interface version, exact Flutter/Dart/Xcode/iOS/Maestro tuple |
| Build and environment | Source-derived build adapter, iOS configuration, approved environment reference/revision and effective-configuration verification method; no secret values |
| Flows | Flow repository, final commit, relative paths and SHA-256; locale and reproducible nonsecret discovered inputs |
| Correlation | Origin issue/PR repository, intended code-delivery targets, run/job/generation and predecessor exploration receipt when applicable |

The tuple receives a deterministic digest using a specified canonical encoding. That digest is a proposed integration identity; it must not be confused with a Git commit, image digest or OCI manifest. The implementation must define schema/version, path normalization and canonical encoding before relying on this hash.

“Atomic” here means that one job admits, builds, validates and reports one immutable tuple. GitHub does not atomically commit or merge two independent repositories. Do not advertise a cross-repository transaction that the implementation cannot provide.

Record both the requested tuple and the resolved tuple. Before build, verify that dependency resolution actually selected the intended package commit/content. A correct package checkout sitting next to the app is not proof that the compiler used it. Moving branch names, PR numbers and unqualified “latest” values are useful discovery inputs but cannot be the accepted build identity.

## Discover the integration mechanism instead of choosing it by guess

The observed declaration uses a Git-tag dependency, currently naming an absent ref. Once the owners correct that dependency, its first adapter should resolve the intended revision and preserve the app's normal mechanism. Inspect the consumed package snapshot, dependency overrides, existing build wrappers and CI definitions to establish how a candidate package commit is tested. The other cases below describe possible future source changes, not alternative explanations of the observed manifest.

The supported adapter must preserve that mechanism or make an explicit reviewed source change:

| Source observation | Required reproducible behavior |
| --- | --- |
| Git dependency | Resolve and record the exact package commit selected by the app's versioned dependency declaration/lock; never assume the branch name identifies immutable content. |
| Path/workspace dependency | Materialize both clean source snapshots into the declared private job layout; verify resolved paths stay inside that layout and the compiled package has the expected content. |
| Hosted dependency | Record immutable release identity and package bytes/integrity; establish provenance to the intended package source commit. A repository checkout alone does not prove which published artifact was consumed. |
| CI-only candidate override | Version and hash the exact override/materialization recipe, preserve original inputs and record the resulting graph. Replay must reconstruct it from immutable inputs. Do not silently call an uncommitted override a clean application commit. |

Only the Git dependency case is currently established for the app/package relationship. The initial adapter should implement it and its observed shared-package closure, not every possible dependency strategy.

Prefer a versioned integration representation that a fresh checkout can reproduce. If the chosen strategy requires an external package checkout, extend snapshot materialization through its existing owner with an explicit declared second source. Do not bypass the prior snapshot protections by accepting arbitrary external symlinks or borrowing a developer's checkout. Generated dependency files belong to the execution directory; required source or lockfile changes must be delivered as code.

## Command and flow ownership

The integrating application is the default proposed owner for executable Maestro journeys and app smoke flows because the tested artifact is its installed iOS application. Confirm the app's current flow layout before using `.maestro/flows/`; that directory is a convention from the accepted native case, not yet an observed Lastmile path.

| Requested work | Source scope | Required validation and delivery |
| --- | --- | --- |
| Resolve an app issue without changing the package | App candidate commit plus unchanged package pin | App tests appropriate to the change and actual app integration validation; deliver app code and preserve the complete tuple. |
| Resolve a package issue | Package candidate plus an explicitly selected app integration snapshot | Package-local checks and the integrating app's affected build/UI checks; deliver the package PR, and an app integration/flow change only when needed. |
| Create a journey for Lastmile behavior | App UI at the app/package tuple, regardless of where the request originated | Real app build, observed UI exploration, app-owned flow delivery and independent replay of the delivered tuple. |
| Run existing E2E flows | Committed flow set plus exact app/package tuple | Rebuild and execute without launching the agent; preserve per-flow results and evidence. Standalone `test-e2e` still requires the shared command-contract implementation identified in the main analysis. |

An issue in the package repository must not silently change the integrating app or publish there using undeclared write authority. The trusted organization deployment declares the integration app, permitted read/write targets and publisher policy; issue prose cannot select arbitrary repositories or credentials. This is a routing/scope contract to implement, not a request for a new human confirmation at each command.

Keep the original issue as the request identity. When code must be delivered to both repositories, link both PRs and their exact tested commits in the result. Publishing a flow in the image repository would detach it from the app that executes it; keep application flows with the application unless its existing source demonstrates an intentionally versioned shared-flow package.

## Package validation is not application acceptance

Run the package's existing analysis/unit/widget/integration checks as discovered from source. Do not invent test commands or require an example app that has not been observed. Those results qualify package behavior within their tested scope.

A passing package suite does not demonstrate that the integrating application links the intended package revision, compiles for iOS, applies staging configuration, exposes usable accessibility semantics or passes the journey. Conversely, an app journey does not replace package-level regression tests that exercise behavior not reached through that UI. Report these suites separately, with JUnit/logs and the source identities they cover.

For a package-only change, the integration result should explicitly say “package commit P validated inside application commit A using integration recipe I.” Do not label the entire app repository as independently changed or validated at an unspecified current main branch.

## Flow creation and independent replay sequence

1. Resolve the source-derived integration contract and select clean app/package exploration snapshots. Hydrate the existing agent with the instructions of the authorized repositories and their distinct ownership boundaries.
2. Build the real integrating app, verify its effective staging environment, install it in the execution's isolated simulator, run the applicable smoke and explore its observed UI with Maestro.
3. Preserve the generated flow and discovered nonsecret replay inputs. Record every app/package source change. A selector change inside the package changes the package snapshot; an app adapter or flow change changes the app snapshot.
4. Deliver the candidate code through the existing code publisher. Freeze the final app commit, package commit, flow digest and integration recipe. The final replay tuple may legitimately differ from the original exploration tuple; record both and their relationship.
5. Start an independent job with new checkouts/VM/simulator. Fetch the exact final tuple and retained dependency closure, reconstruct dependency resolution, verify the intended package and shared-package revisions were consumed, rebuild the app and execute the committed smoke/journey flows. Exclude agent credentials and mutable exploration workspaces/caches. Read-only source access to all declared private dependencies and approved staging inputs remain available as needed.
6. Publish sanitized evidence with the complete tuple, per-flow result, original failures/warnings and cleanup. Link both code targets when applicable and return immutable evidence links to the originating issue.

Candidate source commits can be tested while their PRs are open; this does not authorize promotion of open infrastructure/driver branches into the reusable image. Keep application/package test snapshots distinct from the canonically promoted runtime source requirement.

If either PR head changes after validation, the old receipt remains valid for the old tuple only. A rebase or squash changes the commit identity even when its tree is identical: retain tree equivalence as useful provenance, but do not silently claim that the final commit received the earlier exact-commit replay. Revalidate the resulting final tuple according to the affected scope. The integration owner should coordinate package/app delivery order so merges cannot accidentally replace the tested package pin with another revision.

## Evidence and continuation semantics

The result needs a machine-readable cross-repository manifest beside the ordinary build, flow, JUnit and cleanup artifacts. Include requested/resolved source identities, materialization/lockfile digests, generated-flow location, tested PR heads, effective-environment verification, package checks, app checks and replay results. Record whether the integration strategy used only committed files or an explicitly versioned candidate overlay. Never hide an overlay behind `dirty=false`.

An optional narrative or oversized video remains a warning and does not block code/evidence delivery. A failed package test or app assertion remains failed; applicable independent work and delivery can continue. A dependency mismatch is reported precisely so it can be repaired: running the wrong package revision cannot establish success for the requested tuple. Reuse the unchanged host, image and toolchain acceptance; changing package code does not require rebuilding Xcode or commissioning another executor.

No agent session, staging value, source token or publication credential is sealed into the shared Flutter image. Both repository reads and any PR writes use the existing organization's managed authority at the scopes actually required. Future organizations receive their own bindings; the common image must not inherit this application/package pair as universal defaults.

## Discovery inputs still required from repository inspection

- A concrete compatible Flutter/Dart release and full native dependency/tool closure, derived from the observed constraints and consumed package snapshot.
- Owner correction of the absent `v0.5.1` dependency, its intended package commit, the full resolved shared/transitive dependency graph, reproducible Dart lock/graph and any supported candidate override mechanism. Repository identity and the 18 directly declared shared refs have already been resolved.
- App iOS target/scheme/flavor/entrypoint, bundle ID and effective staging verification; managed delivery of the documented Dart defines, Firebase and native Maps inputs with the approved Lastmile environment.
- Existing package checks and app smoke/flow conventions; accessible UI semantics for the target journey.
- The approved integration app/package routing and existing publisher destinations for issues originating in either repository.

These are source/administrative discoveries, not requests for secrets or manually invented UI test data. Root's repository inspection can fill them within the proposed app/package-plus-dependency-closure execution model.
