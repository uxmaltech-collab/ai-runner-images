# Flutter iOS Hello World

A neutral fixture for native image qualification. It renders a greeting and an
interactive counter. It uses only Flutter SDK dependencies and needs no backend,
account, Maps key, signing identity or agent credentials.

Generate the iOS scaffold with the image-pinned SDK in a new execution directory:

```sh
flutter create --empty --platforms=ios --org tech.uxmal --project-name runner_hello_world --no-pub runner_hello_world
```

Overlay this fixture's `pubspec.yaml` and `lib/main.dart`, run `flutter pub get`,
then `flutter build ios --simulator --debug --target lib/main.dart`. Preserve the
resolved lock, generated project hashes, exact SDK revision and build logs.
Verify the built bundle identifier before running `.maestro/flows/hello-world.yaml`.

Run the app in a newly created simulator as the intended nonadministrator GUI
user. Preserve screenshots and JUnit; delete only that simulator afterwards.
The test must observe count zero and count one after tapping Increment. This is
image qualification, not Last Mile staging or managed-agent authentication.
