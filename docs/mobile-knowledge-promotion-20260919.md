# Mobile knowledge promotion after the resolve canaries

This audit compares Images main `5018467154598e20a2f293da895d2a6f69edec38`
with consumer `3dc11a923ea56a4bee74ed9a24ae6440e06a69f9` and the September 19
[accepted mobile resolve references](../provenance/mobile-resolve-20260919.json).
It extends the September 17 journey harvest; it does not replace its history.

## Completed native follow-up

The table and handoff below describe the earlier audit. Images
[PR6](https://github.com/uxmaltech-collab/ai-runner-images/pull/6) subsequently
merged as `db39042197f68f4bc585a144b152b31648799091`. It includes SwiftLint's
recipe/license/lock, both native build profiles, complete shared frontend
execution, bounded installation deadlines and qualification-child cleanup.
The [native qualification](../qualification/native-tool-recipes-20260919/README.md)
and its summary retain the actual attempts and source identities.

The receiver verified the review handoff and recorded consumer PR331 adoption at
`916b3f4a4311b7d105298d23bc5852186763f260`. That is source-pin adoption;
`runtime_admission=false` remains unchanged. Native reconstruction from the
retained parent is implemented; pristine Apple installation and restoration on
another host are not demonstrated by that evidence. Use the current
[build guide](build-images.md) and [preservation procedure](host-hygiene.md).

## Ownership and remaining work

| Knowledge | Canonical destination | Observed state / next action |
| --- | --- | --- |
| Native tools, combined three-engine layer, then optional Flutter | Images recipes and immutable parents | Already promoted; retain the existing qualified neutral fixture. |
| Android SDK 36, emulator registration, KVM group, privilege reduction and owned cleanup | `recipes/android/` | Already extracted with regression coverage. Preserve the tested algorithms. |
| Java 17 compilation plus Java 21 JVM tests | Android lock, Dockerfile and offline probe | Promoted from the accepted consumer in this change. The original extraction missed the newer test runtime. |
| Consumer adoption from an immutable Images revision | Consumer compatibility lock and materialization checks | Bind recipe bytes and explicit namespace/profile transformations; prove rendering reproduces the exercised consumer. A README link alone is insufficient. |
| Native SwiftLint 0.65.1 and actual lint invocation | Native tools recipe, lock and isolated Darwin fixture | Installed and exercised in the consumer image; shared recipe promotion remains with Mac. Keep license, archive and executable provenance. |
| CLI console relocation, complete wheels/imports and launchers | `recipes/python-runtime`; consumer owns its package identity | The reusable console helper is now canonical here, with real relocation tests. PR322 adopts it by commit/hash; the existing installer/session remains with its owner. |
| Effective PATH, nonadministrator/Aqua execution and unattended tools | Image qualification using canonical session/RPC | Existing native evidence is reusable for unchanged tools. A root version probe does not credit the actual job context. |
| Same image for resolve and create-journey | Consumer command routing, recipe capability closure | Both platforms declare shared routing. Current reference credits resolve; prior journey references retain their own commits/images. |
| Native runtime entry and named Maestro capture collection | Templates control plane and consumer driver | Already canonical in the tested consumer. Images records compatible source identities, not another driver implementation. |
| Clean exact-commit replay and initial UI state | Shared execution contract plus app-owned flow | Both resolve canaries passed. Preserve failed attempts; generic fixtures must not copy private application selectors or data. |
| Recording, full decode, player compatibility and public object verification | Images tools; shared driver/publisher for behavior | Android original WebM played; iOS original HEVC decoded but failed in the tested Chromium. The private H.264 review copy is a distinct derivative. |
| Base identity versus component-update identity | Catalog and native derivative provenance | Mac must retain physical parent and final tuple, recipe commit, runtime source and installed tool hashes separately. |
| Local reconstruction and restoration | Canonical Python entrypoint, recipes and artifact catalog | User selected local image storage. Android and the Linux stack now have actual build/cold-restore receipts. Mac reconstruction remains pending; remote storage is not requested. |

## One native promotion handoff

Mac owns the remaining native recipe delta and its Darwin evidence. Recover the
completed source-update/SwiftLint receipts, extract only reusable installation
and qualification behavior, and exercise it in a disposable derivative of the
preserved parent through the existing owner. Prove real lint execution, relocated
console invocation and changed component closure in the intended user context.
Keep the accepted executor, image and application jobs unchanged during authoring.

Return one source PR (or update the existing PR where it owns the code), exact
heads, sanitized evidence summaries and private original receipt references.
Linux adopts merged sources by pin, verifies materialized byte equivalence and
runs the affected recipe/consumer integration checks. An implementation change
requires its relevant native check; an unchanged Xcode or SDK does not need a
new installation or commissioning loop. Report a new neutral build or restore
as pending until it is actually performed.

## Concurrent runtime migration

Images [PR3](https://github.com/uxmaltech-collab/ai-runner-images/pull/3) and
consumer [PR327](https://github.com/enviaflores/ai-repo-resources/pull/327) propose
the separate Collab Python runtime. At inspection both were open and not adopted.
These accepted-canary records and recipe fixes do not validate that migration.
When it is adopted, rebase its extracted recipes on these locks and preserve the
source-pinning checks instead of creating divergent tool recipes. Its own changed
runtime path still needs qualification.

No host-assignment repository change is part of this promotion. Authentication,
customer environments, application source/flows and raw receipts remain outside
the shared image source. Do not publish licensed image payloads or substitute
source availability for approved artifact distribution.

## Canonical builder follow-up

The [single Python entrypoint](build-images.md) now composes the Linux stack and
Android recipes. Its [qualification](../qualification/image-builder-20260919/README.md)
records actual builds, cold restores, unprivileged tools and cleanup. The native
backend contract is agreed with Mac; SwiftLint and complete native orchestration
still require that source/evidence handoff. Original audit and canary evidence
remain separate from these newer build results.
