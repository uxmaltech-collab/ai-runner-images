# Android resolver and journey runner

One `resolver-storefront-android` image supports both `resolve` and
`create-journey` for `enviaflores/ef-storefront-android`. It inherits the same
digest-pinned `runner-agent-base`, Codex installation, JIT runner entrypoint and
account seed contract as the other repository runners. It creates no second
agent or authentication identity.

`toolchain-lock.json` pins the downloaded bytes: Temurin JDK 17.0.18+8,
command-line tools 19.0, platform-tools 37.0.1, SDK 36 revision 2,
build-tools 36.0.0, emulator 37.1.11, Google APIs API 36 x86_64 revision 7,
and Maestro 2.10.0. This matches the app's JDK 17, AGP 8.11.1 and compileSdk 36
requirements. The application supplies its Gradle 8.13 wrapper. The lock records
official archive URLs, upstream checksums where published and verified SHA-256
for every archive; no `latest` package resolution occurs during installation.

`ef-storefront-android-stack-probe` checks installed tools without starting an
emulator or building the application. The image build runs it without network.
A resolve job uses those tools directly and starts no emulator automatically.

A journey owns its emulator for the lifetime of one command:

```sh
ef-storefront-android-emulator --log-dir "$RUNNER_TEMP/android-explore" -- \
  python3 scripts/validate-maestro.py --commit "$COMMIT" --stage validate \
    --issue "$ISSUE" --staging-properties "$STAGING_PROPERTIES" \
    --flow "$FLOW" --output "$RUNNER_TEMP/android-evidence"
```

The caller supplies the real validator arguments. The wrapper creates an empty,
private AVD outside the checkout, waits up to 600 seconds for boot, exports
`ANDROID_SERIAL=emulator-5554` and the app validator's ownership marker
`EF_ANDROID_EMULATOR_OWNED=1`, executes the command, then stops and reaps only its
owned processes before removing the temporary AVD. Use a new log directory for
each stage; replay gets a fresh AVD. `emulator-result.json` preserves boot status,
the command's exit code and cleanup outcome, alongside original AVD/emulator logs.
Animation-setting failures warn and continue; build/test failures keep their
nonzero status. The publisher owns optional media warnings and evidence delivery.

For an isolated candidate build, the installer accepts `--archive-cache DIR`.
Cache filenames are the original URL basenames. Cache hits receive the same
size and SHA-256 verification before extraction; a corrupt hit fails visibly,
and only a missing file falls back to its pinned upstream URL.

The Linux runtime must expose exactly `/dev/kvm` to this profile. A small image
entrypoint starts as root solely to read that device's group, then immediately
uses `setpriv` to enter the inherited `/entrypoint.sh` as UID/GID 1001 with that
supplemental group. It retains `no-new-privileges`; the emulator wrapper requires
nonroot device access and never escalates. It never changes device ownership/mode or host groups.
No privileged container, host networking, Docker socket or published emulator
port is required. Actual KVM boot, app build, authenticated agent and journey
remain part of the separately authorized E2E, not claims of the static probe.

Official tool contracts: [SDK manager](https://developer.android.com/tools/sdkmanager),
[emulator command line](https://developer.android.com/studio/run/emulator-commandline),
[acceleration](https://developer.android.com/studio/run/emulator-acceleration),
and [Maestro installation](https://docs.maestro.dev/maestro-cli/how-to-install-maestro-cli).

## Shared recipe owner

The neutral tool recipe and qualification knowledge now live in
[`uxmaltech-collab/ai-runner-images`](https://github.com/uxmaltech-collab/ai-runner-images/tree/fef3c6c6754ea1a459cc982df848b6f6561fbce8/recipes/android).
The extraction preserves the reviewed tool algorithms and lock with neutral names.
This consumer retains its exercised Dockerfile and app adapter until a separately
qualified neutral image is built and explicitly adopted; no image digest changes
are implied by the documentation/source promotion.
