# Sources and verification scope

Analysis performed on 2026-09-16. Existing local accepted receipts were reused; no native jobs, installations, tests or CI workflows were run for this analysis.

## Selected Flutter repositories: follow-up discovery

The user selected `enviaflores/ef-lastmile-flutter` and `enviaflores/lastmile-drivers-pkg-flutter`. Three sequential grouped GraphQL reads at 16:51–16:54 UTC inspected source manifests, relevant build/configuration files, repository identity and dependency refs. Immutable source links are in [the acceptance case](LASTMILE-FIRST-ACCEPTANCE.md); request/response digests and resolved direct refs are in [the discovery receipt](provenance/lastmile-discovery.json). Raw private extracts stay outside the portable analysis archive. No dependency fetch, app execution, GitHub write or CI dispatch occurred.

## Accepted operational reference

- [Canary completion comment](https://github.com/enviaflores/ef-storefront-ios/issues/2343#issuecomment-5693038325).
- [Successful workflow 35059345840](https://github.com/enviaflores/ef-storefront-ios/actions/runs/35059345840).
- [Flow PR2367](https://github.com/enviaflores/ef-storefront-ios/pull/2367), accepted flow commit `382ab9e32f594996c6ed6fbaa92c1ed9bf41bd28`.
- [Immutable published manifest](https://github.com/enviaflores/collab-resources/blob/c6c3553934144b3981236bb5e4c7b1f04cb3a967/journeys/ef-storefront-ios/issue-2343/run-35059345840-1/job-104684064756/manifest.json).
- [Consumer source at the accepted commit](https://github.com/enviaflores/ai-repo-resources/tree/3a3e163793d85a2110a7de5098ffe2a2f90b2f3b).
- [Control-plane template source at its accepted pin](https://github.com/uxmaltech-collab/ai-templates-resources/tree/5012de06512f8590da3d5de43b4a790f963b0bec).

The full per-component ownership/pin and historical receipt indexes are in the baseline and lessons documents. Multiple component pins and the original image installer source must remain distinct; one latest templates commit does not replace their historical provenance.

## Current repository discovery

One grouped, read-only GraphQL request at 2026-09-16T16:04:04Z listed all 22 uxmaltech-collab repositories and the EnviaFlores consumer head. Pagination was complete. Original response SHA-256: `cd3ca5bd335c2e68859a3b41bf0d44f05b7203156ed8465a2aafe34a991cef42`.

- Consumer main still pointed to `3a3e163793d85a2110a7de5098ffe2a2f90b2f3b`.
- Templates main pointed to `a1efb6d0eeb2ac2c37531cd8419d841379fc196c`; this is newer catalog metadata, not a tested runtime promotion.
- `studio-github-runners` existed with no default branch. No charter/content was inferred from an empty branch response.
- `ai-runner-images` did not appear in the complete repository list.

The raw organization catalog remains in the private analysis working directory and is excluded from the portable proposal package. No repository was created or changed.

## Primary technical references

1. [Flutter iOS setup](https://docs.flutter.dev/platform-integration/ios/setup): Xcode, platform/Simulator support and native plugin dependencies.
2. [Flutter iOS flavors](https://docs.flutter.dev/deployment/flavors-ios): shared Xcode schemes and configurations under Flutter flavors. Repo-specific schemes remain source-derived.
3. [Flutter CLI](https://docs.flutter.dev/reference/flutter-cli): build, dependency/cache, doctor and test entry points. Proposed invocations must be verified against the selected pinned SDK.
4. [Flutter integration tests](https://docs.flutter.dev/testing/integration-tests): app-owned Dart integration tests are an additional suite, distinct from external Maestro execution.
5. [Maestro Flutter support](https://docs.maestro.dev/get-started/supported-platform/flutter): native semantics/labels/identifiers and the difference from Flutter Keys.
6. [Flutter semantics identifier](https://api.flutter.dev/flutter/semantics/SemanticsProperties/identifier.html): iOS maps the identifier into the native accessibility identifier.
7. [Tart](https://tart.run/): macOS/Linux virtualization on Apple Silicon and OCI-compatible image storage.
8. [Tart image automation](https://tart.run/integrations/packer/): optional Packer integration exists. Introducing Packer is not required to discard or replace the project's existing native image installer.

Web references were consulted for current platform capabilities. Their examples using latest versions or tags are not proposed runtime pins. No external page instructions were treated as operational authority.
