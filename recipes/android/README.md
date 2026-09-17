# Neutral Linux Android tool layer

One image supports resolve and create-journey. An emulator starts only when the
job explicitly invokes `runner-android-emulator`; the entrypoint does not start one.
The inherited combined agent base carries Codex, Claude and Grok together.

Build from the repository root with an immutable `RUNNER_AGENT_BASE_IMAGE` and
`RUNNER_SOURCE_COMMIT`. The inherited base must supply Debian/Ubuntu packages,
Python, unzip/tar, the three agents, `/entrypoint.sh` and runner UID/GID 1001.
The existing reviewed toolchain lock binds JDK17, SDK36, emulator and Maestro
archives by size and SHA-256. `emulator-package.xml` registers the direct archive
with avdmanager. Keep licenses subject to the consuming operator's provisioning.

The entrypoint maps only the declared KVM device group and drops to UID/GID1001
with no-new-privileges. Resolve works without KVM. Journey requires declared KVM
and owns a temporary AVD; it refuses an existing emulator and records cleanup.
The offline probe proves tool launch only, never staging or customer acceptance.

`extraction.json` maps the previously exercised consumer implementation to this
neutral namespace. Algorithm bodies and lock bytes are preserved. App driver,
credentials, flows and profile declarations stay downstream. The retained consumer
image was built and exercised; this newly named neutral recipe has not been rebuilt
or published. Its source promotion must not relabel that old image as a neutral build.
