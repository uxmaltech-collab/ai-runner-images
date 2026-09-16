# Image composition and execution

The iOS execution artifact is a macOS/Tart virtual machine image running on Apple hardware. Linux hosts the existing control plane and publisher. The common resolver runs in the ephemeral guest when a task requires code changes or UI exploration.

## Composition boundaries

1. **Tart macOS/Xcode/Maestro base:** compatible macOS/Xcode/Simulator, Java/Maestro and required platform runtimes. Record the actual base image and all tool build identities.
2. **One shared agent-build layer:** install Codex, Claude and Grok-build together, including required Python/wheel, Node and executable/companion closure. Every engine has its exact install source and launch verification recorded. This is one combined layer, not three alternative image variants.
3. **Flutter/Dart capability:** pin the Flutter/Dart SDK and iOS engine/dependency tooling on the exact shared-agent parent. Tools operate in the intended job user's context. Cache writes must have an explicit supported location; protected SDK trees are not implicitly writable.

Each layer's lock includes its immutable parent digest and resulting native image identity. No shared-agent or Flutter layer may silently select a moving parent alias. All three engines are present in the shared agent layer; installation and authentication are separate. No account session, private key, token or job environment is sealed into any layer.

Trusted consumer/profile binding subsequently selects the resource-pack closure, protected driver and organization/repository inputs through supported owner operations. The accepted EnviaFlores `93df87…` image already contains an EnviaFlores pack and app-specific driver. Preserve it as a legacy accepted reference; do not label it the neutral base or infer that it contains Claude/Grok-build/Flutter.

The initial implementation should reuse supported protected payloads and image owner operations. Per-job injection of arbitrary packs is not established by the accepted native canary. A future generic staging interface needs its own implementation and qualification in its canonical owner.

## Execution chain

Trusted declarations select repository, environment, command, image and managed account. Each execution receives an immutable application snapshot and an isolated guest, checkout, simulator and evidence directory. Exploration builds the staging app, verifies effective configuration, observes actual UI and produces an executable flow. Code delivery fixes the final source identity; a separate job rebuilds and replays it without agent credentials. The external publisher verifies bytes and attaches immutable evidence links.

For Lastmile, the app and driver package are distinct source identities, and both use `shared-package-flutter`. A complete build identity includes the resolved dependency graph, not only two repository main heads. See the [cross-repository contract](research/2026-09-16/LASTMILE-CROSS-REPO.md).

## Artifact identities

Keep recipe/source commits, component hashes, native image manifest, disk/config/NVRAM hashes and any OCI distribution manifest separate. Pin compatible toolchain tuples rather than independent `latest` tags. A local admitted image is not automatically available from an OCI registry.

The catalog reports `planned`, observed accepted references and later qualified releases from actual receipts. It is an informational release index, not a replacement for the installed executor's admission contract. A fixture build qualifies only its demonstrated scope; authentication, customer staging and real device-only behavior retain their separate results.

## Continuation

Represent execution, assertions, code delivery, publication and cleanup separately. Missing optional prose or media must not suppress useful delivery. Preserve the first actual error and failed JUnit; continue applicable independent work and bounded repair. Reconcile ambiguous UI actions, publication or cleanup before repeating side effects.

Host commissioning is reused for an unchanged accepted declaration. Image qualification is reused for identical relevant inputs. New applications qualify their adapter, environment and actual behavior without reinstalling the host or Xcode.
