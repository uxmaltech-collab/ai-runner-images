# Android resolver and journey runner

The `runner-resolver-android` image supports both `resolve` and `create-journey` for
an Android application repository. It is the neutral Android layer
([`recipes/android`](../../android/README.md), released once as the recipe `android`)
plus what is specific to a resolver: the journey binding and the helper aliases. The
image carries no Collab runtime (the control plane mounts the host's at job start). The toolchain lock, the emulator registration, the helpers and the
entrypoint exist only in the Android layer; this recipe builds `FROM` that layer's
image (`RUNNER_ANDROID_IMAGE`) and repeats none of them. The layer in turn
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
listed for it. The list is read from the image-owned file
`/etc/runner-android-emulator/marker-aliases` (written at build time) and, joined to it,
from `RUNNER_ANDROID_EMULATOR_OWNED_ALIASES` when the caller passes that variable. The
file is what works through the journey launcher: the pinned runtime starts the helper
with a fixed list of environment variables that does not include the alias variable.

A consumer that still declares a former helper path or marker during its migration
keeps that handling on its side, or has the organization's canon declare the former
path and the planner pass it as `RUNNER_HELPER_ALIASES` (see below). No former name is
written in this repository.

## Plan-time inputs

The repository, the profile id and the application validator of the journey, the former
helper paths and marker names, and the approved digest of the Android layer are
organization data. The planner reads them from the organization's canon and passes them
as build arguments, which the recipe declares in `recipes/manifest.json` under `inputs`:

| Build argument | Fact | Applied by |
| --- | --- | --- |
| `RUNNER_JOURNEY_REPOSITORY` | `journey.repository` | `common/plan-inputs.py journey` |
| `RUNNER_JOURNEY_PROFILE` | `journey.profile` | `common/plan-inputs.py journey` |
| `RUNNER_JOURNEY_VALIDATOR` | `journey.validator` | `common/plan-inputs.py journey` |
| `RUNNER_HELPER_ALIASES` | `helper.aliases` (`ALIAS=TARGET` pairs under `/usr/local`) | `common/plan-inputs.py aliases` |
| `RUNNER_ANDROID_MARKER_ALIASES` | `helper.marker_aliases` (names of the former ownership marker) | `common/plan-inputs.py markers` |
| `RUNNER_ANDROID_IMAGE_DIGEST` | `image_pins.digest` (the approved digest of the Android layer) | `common/plan-inputs.py parent` |
| `RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST` | `builder.resolved_parent_digest` (what the build host observed a tag to resolve to; not a canon fact) | `common/plan-inputs.py parent` |

`/opt/ai-repo-resources/journey-driver.json` is the document the pinned runtime
compares, field by field, with the pack's own declaration of the same journey: a
placeholder or a value that differs makes the journey fail, so the file is never a
template. [`journey-driver.json`](journey-driver.json) in this directory **is** a
template: its constants, and `null` where the three organization facts go. With all
three journey inputs resolved and valid the tool writes the document; with none, or a
partial or invalid set, it writes nothing, the build log carries a warning and the image
is the generic Android resolver, without a binding: nothing of any organization is baked
in, and nothing is kept from a previous build. The build never stops over a binding.

The reference of the Android layer may be a tag or a digest: its spelling only warns. What
is verified is the digest: the one in the reference or, for a tag, the one the build host
observed and passes as `RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST`, compared with the approved
one (`RUNNER_ANDROID_IMAGE_DIGEST`). The build stops when they differ (that image is another
artifact) and when a tag comes without an observed or an approved digest, because nothing
then identifies the bytes it starts from. A digest-qualified reference with no approved
digest only warns.

The pack revision is the last declaration, as in the other resolvers, and no Collab
runtime is installed. Like them, this recipe has no `smoke.sh` yet and no image has been built or
promoted by this source; it needs its own Linux qualification after adoption.
