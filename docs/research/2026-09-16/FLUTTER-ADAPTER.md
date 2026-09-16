# Flutter iOS capability and adapter

No Flutter build was performed for this analysis. The successful reference app is native iOS. The first Flutter application is now `enviaflores/ef-lastmile-flutter`, integrating `enviaflores/lastmile-drivers-pkg-flutter`; both also depend on `shared-package-flutter`. See [observed build requirements and unresolved source ref](LASTMILE-FIRST-ACCEPTANCE.md) and [multi-repository replay](LASTMILE-CROSS-REPO.md). This choice does not require repeating host commissioning.

## Image changes

Add a pinned Flutter SDK revision with its matching Dart and iOS engine artifacts. Record checksums and installation provenance. Precache the iOS artifacts in image preparation, then verify that the intended nonadministrator guest session can use them without changing protected toolchain directories. An SDK cache that silently requires privileged writes during the job is not a finished image.

Determine the app's native dependency path from its source. Pin Ruby/Bundler/CocoaPods when the application uses Pods, and preserve `Podfile.lock`; support the application's SwiftPM configuration and resolved dependencies when applicable. Keep `pubspec.lock` and SDK constraints authoritative. Do not use `flutter upgrade` or an unpinned package update as part of normal job startup.

The current native installer and guest expect an exact tool set. Flutter must be introduced through a template-owned extension to tool/capability validation and the actual guest probe. Installing a binary without declaring and checking it is insufficient. The existing code-mode companion, ordinary CLI wheel closure, session, keychain and Maestro bridge remain part of the runtime.

## App-owned adapter contract

The following names describe a proposed interface, not commands currently available in the pack.

| Operation | Inputs | Required output |
| --- | --- | --- |
| Discover build | Exact checkout; SDK/lockfiles; app manifest | App root, SDK requirement, flavor/scheme/configuration, Dart target, dependency strategy, expected bundle ID |
| Build simulator app | Declared toolchain; private staging inputs; exact commit | Real simulator `.app`, actual bundle ID, build log and digest, source/tree identity, configuration probe |
| Verify environment | Built artifact and approved staging contract | Effective environment/API comparison and method used; no secret values |
| Prepare UI | New simulator ID; built `.app`; explicit locale and permission policy | Installed app, screenshot and UI hierarchy showing readiness |
| Explore/create | Original issue criteria and ordinary hydrated agent | One executable flow and reproducible nonsecret discovered inputs |
| Replay existing | Clean exact commit; flow set; same environment revision | Build and per-flow JUnit/evidence, process/simulator cleanup |

An illustrative build entry point is `flutter build ios --simulator --debug --flavor <declared-scheme> --target <declared-dart-entrypoint>`. Validate supported flags against the chosen pinned SDK and the repository's wrapper. Discover the actual app output rather than hardcoding `Runner.app` for all applications. The simulator artifact is the target; an App Store IPA/signing pipeline is separate work.

For the selected Last Mile source, omit `--flavor`: only `Runner` and Debug/Profile/Release were observed. Its proposed build uses `--target lib/main.dart --dart-define-from-file=.env.json`, with separately delivered native Maps configuration. The generic flavor example above applies only to repositories that actually declare such a scheme.

For native iOS, the reference adapter checks compiled `Environment`/`ApiHost`. In Flutter, environment logic may reside in Dart defines, assets or generated configuration. Passing a staging flag or checking only an xcconfig file cannot establish the actual app's API. Each adapter must supply a verifiable effective-configuration probe appropriate to that app, tied to the built artifact and, where needed, the running staging app. Proposed diagnostic support must not expose secrets or ship a production bypass.

Staging configuration is reusable at organization/repository/environment scope. Preserve multiline configuration bytes. Do not ask an operator to supply product names, catalog URLs or location links merely because Flutter is new; the authenticated agent discovers authorized staging inputs through code and observed UI, then records the reproducible nonsecret inputs with the flow. Any required test identity remains a managed environment reference.

## Maestro visibility

Maestro uses the Flutter semantics exposed through native accessibility. Flutter `Key`/`ValueKey` are not equivalent to native accessibility selectors. Use observed text or `Semantics(identifier: ...)`/semantic labels, and verify the actual hierarchy on the selected Flutter/Xcode/Maestro tuple. [Maestro's Flutter documentation](https://docs.maestro.dev/get-started/supported-platform/flutter) and [Flutter's identifier API](https://api.flutter.dev/flutter/semantics/SemanticsProperties/identifier.html) support this distinction.

A neutral fixture should include a list, a collapsible menu, navigation, asynchronous loading and a permission/onboarding state. Its acceptance must demonstrate screenshot, hierarchy inspection, interaction and assertions through the same agent bridge used by the real job. Merely installing Maestro or passing `flutter doctor` does not test that integration.

If selectors require a source change, commit the change and qualify the resulting snapshot. Keep locale explicit and avoid a Spanish test data value against an English catalog. Recover overlay state by observation before an action; do not resend an action after an ambiguous response.

## Required acceptance

1. Use the nonadministrator GUI/session context launched by the existing executor. Establish tool readiness and the complete hydration/companion closure.
2. Build and install a real Flutter staging app in the execution's simulator. Verify its effective configuration.
3. Run a baseline smoke, then have the ordinary resolver inspect UI and create a journey with assertions.
4. Deliver the resulting commit through the existing code publisher and execute a fresh rebuild/replay without agent credentials.
5. Exercise standalone `test-e2e` after its command contract is implemented. Its execution must not manufacture an exploration predecessor.
6. Verify external immutable publication and native cleanup. Reuse unchanged host/image checks; preserve failed checks and diagnostic evidence.

Flutter's built-in `integration_test` is an additional app test suite when a repository uses it; it is not a substitute for the required external Maestro journey. See [Flutter integration testing](https://docs.flutter.dev/testing/integration-tests).
