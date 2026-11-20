# Android resolver and journey runner

The `runner-resolver-android` image supports both `resolve` and `create-journey` for
an Android application repository. It is the neutral Android layer
([`recipes/android`](../../android/README.md), released once as the recipe `android`)
plus what is specific to a resolver: the journey binding, the helper aliases and the
Collab runtime. The toolchain lock, the emulator registration, the helpers and the
entrypoint exist only in the Android layer; this recipe builds `FROM` that layer's
image by digest (`RUNNER_ANDROID_IMAGE`) and repeats none of them. The layer in turn
inherits the digest-pinned `runner-agent-base`, the Codex installation, the JIT runner
entrypoint and the account seed contract, and creates no second agent or
authentication identity. The toolchain, the offline probe, the emulator ownership and
the KVM entrypoint are documented in the layer's README.

## Helpers

The stable neutral helpers, installed in `/usr/local/bin` by the Android layer, are:

| Capability | Path |
| --- | --- |
| Emulator owner for one command | `/usr/local/bin/runner-android-emulator` |
| Offline stack probe | `/usr/local/bin/runner-android-stack-probe` |

They are also listed under `helpers` in [`recipes/manifest.json`](../../manifest.json),
so a planner resolves the helper path from the released recipe instead of copying it.
The wrapper exports `ANDROID_SERIAL=emulator-5554` and the ownership marker
`RUNNER_ANDROID_EMULATOR_OWNED=1`, and the same value under each former marker name
listed in `RUNNER_ANDROID_EMULATOR_OWNED_ALIASES`.

A consumer that still declares a former helper path or marker during its migration
keeps that handling on its side, or has the organization's canon declare the former
path and the planner pass it as `RUNNER_HELPER_ALIASES` (see below). No former name is
written in this repository.

## Plan-time inputs

The repository, the profile id and the application validator of the journey, and the
former helper paths, are organization data. The planner reads them from the
organization's canon and passes them as build arguments, which the recipe declares in
`recipes/manifest.json` under `inputs`:

| Build argument | Fact | Applied by |
| --- | --- | --- |
| `RUNNER_JOURNEY_REPOSITORY` | `journey.repository` | `common/plan-inputs.py journey` |
| `RUNNER_JOURNEY_PROFILE` | `journey.profile` | `common/plan-inputs.py journey` |
| `RUNNER_JOURNEY_VALIDATOR` | `journey.validator` | `common/plan-inputs.py journey` |
| `RUNNER_HELPER_ALIASES` | `helper.aliases` (`ALIAS=TARGET` pairs under `/usr/local`) | `common/plan-inputs.py aliases` |
| `RUNNER_ANDROID_MARKER_ALIASES` | `helper.marker_aliases` (names of the former ownership marker) | `runner-android-emulator` |

`/opt/ai-repo-resources/journey-driver.json` is the document the pinned runtime
compares, field by field, with the pack's own declaration of the same journey: a
placeholder or a value that differs makes the journey fail, so the file is never a
template. [`journey-driver.json`](journey-driver.json) is the prior verified binding.
With all three journey inputs resolved and valid the tool writes them over it; with
none, or with a partial or invalid set, it keeps the prior verified binding unchanged
and the build log carries a warning, so an image built without the canon is exactly
the image that was verified before. The build never stops over a binding.

The Collab runtime and the pack revision are the last layer, as in the other
resolvers. Like them, this recipe has no `smoke.sh` yet and no image has been built or
promoted by this source; it needs its own Linux qualification after adoption.
