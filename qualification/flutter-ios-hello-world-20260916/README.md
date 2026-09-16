# Flutter iOS image qualification — passed

The final cumulative image built and ran the real Flutter Hello World app as a nonadministrator in the guest's Aqua session on 2026-09-16. Maestro verified the initial screen, tapped **Increment**, and observed the counter change from **0** to **1**. JUnit reports one passing test, zero failures and no skipped cases. The owned simulator and disposable qualification VM were removed after evidence export.

| Component | Verified result |
| --- | --- |
| Native base | macOS 26.6.2; Xcode 26.5 / 17F42; iPhone 17 simulator with iOS 26.5 / 23F77; Maestro 2.10.0 |
| Combined agent layer | **Codex 0.151.0 + Claude 2.1.266 + Grok-build 1.0.24 together**; payload hashes and all three native CLI launches passed |
| Flutter layer | Flutter 3.47.4; Dart 3.13.3; protected seed cloned into the job user's writable SDK/cache |
| Execution identity | UID 502 / GID 20; nonadministrator; real console and Aqua session; isolated from the host executor account |
| Application | `tech.uxmal.runnerHelloWorld`, built for iOS Simulator; Xcode build completed in 145.3 seconds |
| UI assertions | `Hello World`, `Count: 0`, tap `Increment`, `Count: 1` |
| Cleanup | Owned command groups absent, simulator absent, normal guest shutdown with Tart exit 0, qualification VM absent |

Image artifact-manifest SHA-256:

`33fb89bdccd573057c11388bdf2dc243fbf8a4d5ceea46d2c577c93e2e2dd9be`

Recipe and qualification source commit: [`4e41365a51b5476b3ffe717ff81624559d5d3254`](https://github.com/uxmaltech-collab/ai-runner-images/commit/4e41365a51b5476b3ffe717ff81624559d5d3254). Local image name: `uxmal-flutter-dart-v4-20260916`. [The catalog](../../catalog/images.json) records its config, NVRAM and disk identities, physical repair ancestry and the three logical layers.

## Evidence

- [Qualification summary and original receipt digests](summary.json)
- [Actual build/UI result and command records](evidence/hello-world/result.json)
- [JUnit](evidence/hello-world/maestro/junit.xml) and [executed flow](evidence/hello-world/fixture/.maestro/flows/hello-world.yaml)
- [Build log](evidence/hello-world/commands/flutter-build.stdout.log) and [Maestro log](evidence/hello-world/commands/maestro-test.stdout.log)
- [All three agent CLI checks](evidence/agent-versions.json), [eight-tool readiness](evidence/owner-tools.json) and [private SDK clone](evidence/private-sdk-clone.json)
- [VM cleanup](evidence/qualification-vm-cleanup.json) and [publication byte manifest](evidence/PUBLICATION-MANIFEST.json)

![Hello World after the verified counter increment](evidence/hello-world/hello-world-final.png)

The selected evidence contains 96 original Hello World files. The single large simulator system log remains in the verified private archive, with its byte count and SHA-256 recorded in [the selection summary](evidence/SUMMARY.json). The retained source manifest is explicitly an inventory of the original complete export, not a claim that the omitted file is in Git.

## Scope and recovery

The fixture ran from **18:47:12 to 18:52:20 UTC**. Agent checks launched all three pinned CLIs without authentication; the fixture itself did not invoke a model. No job credential or runtime account was sealed into the reusable image. These local image records and this neutral application test do not constitute registry publication, production executor admission or Lastmile staging acceptance.

Earlier directory-permission, shutdown-persistence and SDK-symlink failures are retained in [composition provenance](../../provenance/layer-composition-recovery-20260916.json). The final image includes the narrow symlink repair, verified with seven focused regressions. One v4 pre-shutdown account snapshot failed before creating a shutdown intent; its later read-only snapshot passed, and only the unconsumed shutdown was retried. The original failure and recovery receipts remain referenced in `summary.json`.

The sealed source tuple, production executor configuration and production image metadata were verified unchanged after qualification. To repeat on a new derivative, use the existing [qualification session adapter](../../recipes/qualification-session/README.md) and [committed fixture](../../fixtures/flutter-ios-reference/README.md); retain fresh receipts and delete only the disposable resources created by that run.
