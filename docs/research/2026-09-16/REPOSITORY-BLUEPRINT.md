# Proposed repository contents

Proposed owner: `uxmaltech-collab/ai-runner-images`. Proposed initial visibility: private. The following is a repository blueprint, not a generated production implementation.

```text
README.md
AGENTS.md
CODEOWNERS
CHANGELOG.md
docs/
  architecture.md
  ownership.md
  commissioning.md
  image-compose-and-release.md
  repository-onboarding.md
  recovery.md
  diagnosis-by-stage.md
  evidence-and-retention.md
  decisions/
catalog/
  images.yaml
  compatibility.yaml
recipes/
  macos-xcode-maestro/
  flutter-ios/
  consumer-pack/
locks/
  <accepted-release>.json
contracts/
  recipe.schema.json
  capability.schema.json
  app-adapter.schema.json
examples/
  organization-binding.example.yaml
  native-ios-app.example.yaml
  flutter-ios-app.example.yaml
fixtures/
  flutter-ios-reference/
  native-interface-regressions/
reference-cases/
  enviaflores-ios-2343/
    acceptance.json
    source-map.json
    failure-regressions.md
    archive-index.json
    sanitized-receipts/
qualification/
  <image-digest>/
    inputs.json
    results.json
    cleanup.json
scripts/
  <thin wrappers over canonical owner operations>
```

Keep shared implementation code in its canonical owner. Scripts here compose recipes, verify immutable inputs and call existing owner adapters. They do not independently create accounts, rewrite sshd, operate a second broker or implement a second resolver. Native image building remains a macOS task; a future Linux builder recipe can coexist in a different platform directory.

## Catalog and lock contents

An image record identifies the immutable parent, backend/architecture, recipe and shared-component commits, tool versions/builds and hashes, compatible consumer interface versions, runtime/resource observations, native manifest and artifact identities, distribution URI/digest, qualification receipt and previous accepted image. Record where it was actually qualified and whether a cold-start/recovery result exists. Do not represent documentation or a static descriptor as installed readiness.

Keep native image digest, OCI distribution digest, disk/config/NVRAM hashes and application commit as different fields. Preserve exact dependency closure, including Python wheels, ordinary hydration libraries and Codex companions. A pack/profile derivative also records its resource-pack source and descriptor digest.

The first catalog entry is the accepted EnviaFlores reference. Neutral toolchain and Flutter entries remain `proposed` until built and tested. Unknown macOS/Tart/Flutter details are explicit missing lock inputs, never invented defaults.

## Consumer declaration

Each organization should own its deployed binding. The shared repository supplies a schema and examples. These fields are a proposed logical model, not accepted YAML for the current CLI:

```yaml
# Design example only; NOT accepted by the current runtime.
status: proposed
organization: <organization>
repository: <organization>/<application>
resource_pack:
  repository: <organization>/<resource-pack>
  canonical_commit: <merged-commit>
runtime:
  profile: <declared-existing-agent-profile>
  backend: macos-tart
  image: <accepted-consumer-image-reference>
  native_manifest_digest: <accepted-digest>
  engine_account_ref: <organization-managed-codex-account>
application:
  adapter: flutter-ios
  app_root: <relative-project-root>
  sdk_lock: <repository-sdk-lock-path>
  scheme: <shared-xcode-scheme>
  flavor: <declared-flavor>
  dart_target: <relative-entrypoint>
  bundle_id: <expected-simulator-bundle-id>
  environment: staging
  environment_ref: <managed-private-environment-reference>
  effective_environment_probe: <app-owned-probe>
  smoke: <committed-smoke-flow>
  flows_root: .maestro/flows
  locale: <declared-test-locale>
commands:
  resolve: <declared-native-resolver-route>
  create-journey: <declared-native-journey-route>
  test-e2e: <future-declared-existing-flow-route>
publication:
  policy_ref: <organization-owned-evidence-policy>
```

The compiler/validator for this declaration belongs to the appropriate shared owner. Add a second organization fixture with distinct pack, bundle ID, environment reference and publication destination to prove that defaults cannot leak EnviaFlores configuration into another tenant.

## Durable history and recoverability

Separate four artifact classes:

| Material | Storage | Required reference |
| --- | --- | --- |
| Recipes, source maps, sanitized summaries, regression fixtures | This Git repository | Commit and file digest |
| macOS/Tart images and offline distributable tool payloads | Approved private OCI/image/artifact store | Format, byte sizes, digests, access mechanism and verified restore receipt |
| Original private logs, JUnit, plans and operation receipts | Scoped immutable private archive | Archive manifest, SHA-256, retention/access owner and successful retrieval record |
| Customer journey artifacts | Customer app repository and approved evidence publisher | Flow commit, evidence commit, immutable issue links |

Preserve original failed attempts and consumed authorization records in the private archive, not as authorization for future operations. Keep a source-to-fix map so a future operator can find the real corrective PR and regression without replaying every historical attempt. Existing local checkpoint paths and SFTP exports are recovery inputs, not proof that the new repository already stores their bytes.

For oversized video, define encoding/segment/thumbnail policy before capture. Verify the retained original or private archive before deleting the execution's resources. An `originals_preserved` field by itself is not a later restore test. Optional media must not hold code delivery hostage, but any omission remains visible.

## Onboarding sequence

1. Discover app build settings, SDK/dependency locks, expected staging behavior, accessibility and existing smoke flows from source.
2. Bind the organization's existing GitHub/OIDC/broker/publisher authority and its environment reference once.
3. Select a qualified toolchain tuple and compose a compatible consumer/profile derivative through existing image operations.
4. Run the app-specific build, environment and UI acceptance, followed by committed-flow replay and verified publication.
5. Register the exact accepted combination. Reuse it for subsequent issues; update only changed inputs.

The new organization supplies its repository identity and administrative bindings. It does not need to supply manually invented UI data or a new Codex session per issue. Agent identities and resource ownership remain in their existing catalogs.
