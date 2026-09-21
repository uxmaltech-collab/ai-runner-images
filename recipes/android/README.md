# Neutral Linux Android tool layer

One image supports resolve and create-journey. An emulator starts only when the
job explicitly invokes `runner-android-emulator`; the entrypoint does not start one.
The inherited combined agent base carries Codex, Claude and Grok together.

Build from the repository root with an immutable `RUNNER_AGENT_BASE_IMAGE` and
`RUNNER_SOURCE_COMMIT`. The inherited base must supply Debian/Ubuntu packages,
Python, unzip/tar, the three agents, `/entrypoint.sh` and runner UID/GID 1001.
The existing reviewed toolchain lock binds JDK17, JDK21, SDK36, emulator and Maestro
archives by size and SHA-256. `emulator-package.xml` registers the direct archive
with avdmanager. Keep licenses subject to the consuming operator's provisioning.

The entrypoint maps only the declared KVM device group and drops to UID/GID1001
with no-new-privileges. Code-only resolve works without KVM. Visual resolve and journey require declared KVM
and owns a temporary AVD; it refuses an existing emulator and records cleanup.
The offline probe proves tool launch only, never staging or customer acceptance.

`extraction.json` maps the previously exercised consumer implementation to this
neutral namespace. Algorithm bodies and lock bytes are preserved. App driver,
credentials, flows and profile declarations stay downstream. The retained consumer
image was built and exercised. The neutral recipe has now been built and
cold-restored through the [canonical Python entrypoint](../../docs/build-images.md);
its [separate receipts](../../qualification/image-builder-20260919/README.md) do not
relabel the consumer image or credit a new application journey.

## Compile and test Java runtimes

The default `JAVA_HOME` stays on Java 17. SDK 36 Robolectric tests require the
separately pinned Java 21 toolchain at `/usr/lib/jvm/temurin-21`; Gradle can discover
that directory and `JAVA21_HOME` names it explicitly. The offline image probe
launches both versions as the runner. A successful app compilation alone did
not establish that its JVM tests had the required runtime.

The September 19 resolve canary exercised these consumer recipe bytes. See
[the accepted reference](../../provenance/mobile-resolve-20260919.json).
This is consumer E2E evidence. Neutral tool-layer build/restoration is recorded
separately and uses local artifact storage.
