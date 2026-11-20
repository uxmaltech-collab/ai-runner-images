# Build images from their source of truth

Run the Python entrypoint in this repository. Local image storage is supported;
a remote registry or backup bucket is not a prerequisite. Preserve original
artifacts and receipts. This builds and qualifies images, without admitting them
into an executor or deploying a control plane.

**Which route.** The route for the Dockerfile recipes of
[`recipes/manifest.json`](../recipes/manifest.json) is the organization's console:
it orders the build on its builder node, which builds the released recipe tree and
keeps the image in the console's registry; hosts pull by digest and never build.
This entrypoint is the transition route, valid until the organization's console has
its registry and a builder node, and it stays the only route for the native macOS
profiles (Tart virtual machines, not OCI images). Everything below describes the
entrypoint.

```sh
python3 scripts/build-images.py plan --profile android \
  --inputs /private/build-inputs.json --work-dir /private/new-image-build
python3 scripts/build-images.py build --profile android \
  --inputs /private/build-inputs.json --work-dir /private/new-image-build
```

Use Python 3.12+, a clean committed checkout and a new private work directory
outside the checkout. `plan` is read-only. `build` records the source commit and
input digest in `PLAN.json`, retains command logs and writes `RESULT.json`,
including failures. No recipe relies on a checkpoint script or personal login.
Inputs contain paths and immutable identities, never secret values.

## Linux and Android

Copy the relevant example from [examples/build-images](../examples/build-images).
Install Docker/buildx, containerd, iproute2 and util-linux on the build host. Cold
restoration needs permission to create a private network namespace and an
independent local daemon; it never reconfigures the host Docker service. Ensure
free space for the build, its local archive and a second unpacked image store.
Public network access is needed for pinned tool archives, package installation
and locked Python wheels. Read the [Linux stack prerequisites](../stacks/linux-control-plane/README.md)
for root image provisioning and the pinned Templates source. No GitHub App or
agent authentication is needed for these offline qualification fixtures.

| Profile | Entire operation |
| --- | --- |
| `linux-control-plane` | Materialize the pinned shared source, build the base, combined agents, CI runner and control plane, save an archive, restore into empty independent stores and run offline qualification. |
| `android` | Build and qualify that parent stack, build the neutral Android layer, save its archive, cold-restore it and run tools as UID 1001. |
| `macos-ios`, `macos-flutter` | Compose from a declared local Tart parent, install or verify SwiftLint and the combined engines, optionally add or reuse Flutter/Dart, seal the stopped tuple, qualify real lint in a disposable nonadministrator session, and clean that child. See the [native backend inputs and parent prerequisites](../recipes/macos/README.md). |

An existing Linux stack `BUILD.json` can be supplied as `inputs.parent_receipt`
for Android. The recipe checks its Templates lock, image ID, digest reference
and complete layer list before reusing it. This is the incremental path for
unchanged parents. Omit it to build the parent graph in the same invocation.
`inputs.recipe_commit` may select an exact earlier 40-character image-source
commit when qualifying an unchanged Android recipe; the result distinguishes
that recipe commit from the orchestration commit.

The restored Android fixture verifies Java 17/21, SDK, emulator executable,
Maestro and all three agent CLIs without credentials. Tool launch is not an
emulator journey or an application build; those outcomes are recorded separately.
The control-plane fixture is likewise offline and does not register a GitHub
runner. Existing application and GitHub E2E records retain their own provenance.

`BUILD.json` binds the image reference, ID, layers, parent and archive hash/size.
`restore/RESTORE.json` reports the initially empty store, observed tools, owned
process cleanup and preservation of the host bridge. The restored daemon runs
in a verified separate network namespace: `--bridge none` alone is insufficient.
Both archives and daemon stores remain local, with their logs available for
inspection. No registry push or runtime replacement occurs.

A source rebuild uses the locked tool inputs and recipes. It is not a guarantee
of identical OCI bytes: upstream APT/npm transitive inputs are not snapshot-locked.
Restoring the preserved archive does require the original image ID and layers.
Keep these two reproducibility claims distinct.

## Resolver and CI recipes

`scripts/build-images.py` has no profile for the Dockerfile recipes of the manifest
other than the Android layer: `plan --profile runner-resolver-android` is rejected as
an unknown profile, and `--profile android` builds the neutral Android layer only. Until
the console builds them, a build host builds one of these recipes with Docker from the
**release tree**. No `docker build` is run by the tests or by the release procedure, and
no backend qualifies the result: these recipes have no `smoke.sh` and an image built this
way is unqualified.

1. **Context.** A checkout of the release tag, or the extracted tree tar of the release,
   is the context: each recipe sits at its `path` with its `shared` paths beside it, and
   every Dockerfile `COPY` source is a path of that tree
   (`python3 scripts/check-recipe-manifest.py` warns about one that is not). The recipes
   that install Collab (`context_inputs: ["collab-release"]` in the manifest) also need
   the exact release as `collab-release/` at the root of the context, verified first
   against [`compatibility/collab-runtime.lock.json`](../compatibility/collab-runtime.lock.json).
   The entry's `context` says what fills it, in the shape of a container recipe's
   `version.json` `build.context`: `{"name": "collab-release", "kind": "artifact",
   "component": "uxmaltech-collab/cli", "version": ">=0.2.3"}` (the release artifact set of
   the Collab runtime, a version the recipe works with). Which version an organization
   runs is its own choice: the console takes the one its adoption names (else the one it
   adopted) and records it in the build; the recipe never pins it. The directory holds the
   files of that release's artifact set as they are published, flat: `install.py`, its
   `SHA256SUMS`, `release-manifest.json`, `collab-runtime.lock.json` and the wheels;
   `install.py install --artifacts /opt/collab-release` reads them there.
2. **Parent.** `parent` in the manifest names what the base is and the build argument
   that carries it, in one of three forms:

   | Form | The base | Example |
   | --- | --- | --- |
   | `{recipe, version, build_arg}` | the image of another recipe of this manifest | `runner-agent-base` on `runner-base` |
   | `{component, recipe?, version, build_arg}` | the image of a recipe of another released component (its release index key; `recipe`, its manifest entry, when that tree holds several) | none here today |
   | `{pin, build_arg}` | an image no recipe builds (an operating-system or third-party image), by a neutral profile name | `runner-base` on its OS image: `{"pin": "runner-base-os", "build_arg": "RUNNER_BASE_OS_IMAGE"}` |

   A pin is the organization's own: it declares the digest under `image_pins` (`profile`:
   the pin's name) in its canon, and the recipe names no registry, tag or digest. The
   check warns about a `FROM ${ARG}` with no default that is not the parent's build
   argument. The reference may be a tag or a digest; its spelling is
   only metadata. What matters is the digest it resolves to: pass the approved digest
   (the organization's image pin) and, for a tag, the digest the build host observed:

   ```sh
   docker image inspect --format '{{index .RepoDigests 0}}' <parent reference>
   python3 recipes/collab-runners/common/plan-inputs.py parent \
     --reference <parent reference> --approved sha256:<approved> --resolved sha256:<observed>
   ```

   The command warns about a tag, or about a digest it cannot verify, and goes on. It
   stops (exit 1) only when the resolved digest is not the approved one: that image is
   another artifact. The same check runs inside the build of `runner-resolver-android`
   (`RUNNER_ANDROID_IMAGE_DIGEST`, `RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST`).
3. **Plan-time inputs.** Each fact an organization owns is a `--build-arg` named under
   `inputs` in the manifest; the values come from the organization's canon through its
   planner, never from this repository. Without them the recipe still builds and warns.
4. **Build.**

   ```sh
   docker build -f recipes/collab-runners/runner-resolver-android/Dockerfile \
     --build-arg RUNNER_ANDROID_IMAGE=<parent reference> \
     --build-arg RUNNER_ANDROID_IMAGE_DIGEST=sha256:<approved> \
     --build-arg <input>=<value> ... -t <image> .
   ```

   The builder labels the image with `collab.recipe.component`, `collab.recipe.version`,
   `collab.recipe.tree_digest` and `collab.build.id` (`--label`), and records the digest
   of the result for the registry the organization already uses.

## Swift package cache for the resolver image

The collab runner image a macOS executor runs (`macos_host image-build` in
Collab infra 0.3.156 or later) accepts `--cache-tree <directory>`: a tree the
host prepared that the image carries at `/opt/collab/cache`. For an iOS
resolver, warm it on the build host with the host's Xcode and the app's
checkout before the build:

```sh
python3 -m collab_infra.runners.spm_cache --project /path/to/App.xcodeproj \
  --output /private/image-cache --developer-dir /Applications/Xcode.app/Contents/Developer
```

`spm_cache` resolves the project's Swift packages once into `<output>/spm`,
the directory a job's `xcodebuild -packageCachePath` reads, and records the
`Package.resolved` digest in `<output>/receipt.json`. A validator or an agent in
the guest that passes `-packageCachePath /opt/collab/cache/spm` then resolves
and fetches nothing from the network. The cache is public tool and dependency
bytes only; it holds no credential, no app source and no derived build. Warm it
again when `Package.resolved` changes, and rebuild the image to carry it.

## Native composition contract

The backend interface is `build(inputs, work, root, commit, *, profile)` and
returns a JSON-serializable result with `status`, artifacts, qualification and
cleanup references. `root` is the committed image SoT; `work` is a new private
directory. The frontend calls only the profile's fixed backend.

The native backend uses `scripts/tart-layer.py` and the existing image/session
owners to compose macOS/Xcode/Maestro, the combined Codex/Claude/Grok layer, then
optional Flutter/Dart. Inputs declare the parent tuple, tool payloads, the consumer's adopted
harness pins and host binding; no host identity or private endpoint is baked into a recipe. Document
how to obtain the licensed macOS/Xcode parent and which retained artifacts are
still prerequisites. A retained parent does not establish a clean-machine build.

Qualification runs in a disposable nonadministrator guest session. Normal
shutdown and stopped config/disk/NVRAM hashes bind the output. Preserve accepted
images and use a derivative for changed components. SwiftLint and CLI relocation
must be recipe inputs/steps, not checkpoint-only repairs. The generic Python
console relocation recipe is in `recipes/python-runtime`; the consumer owns its
package name, entry point and final destination.

## Development coverage

Follow [autonomous native development](native-development.md) to own the complete
mechanical repair loop and distinguish tool qualification from current-runtime
and real GitHub integration. The existing native qualifier checks session/tools
and SwiftLint; it does not yet supply the complete Collab mechanical fixture.
Do not turn that implementation gap into an acknowledgment or report gate.

## Recovering a failed attempt

Read `RESULT.json`, component logs and completed receipts first. Do not overwrite
the work directory or blindly repeat native lifecycle operations. Reuse a verified
parent receipt for an unchanged Linux parent and start a new derived build for a
changed recipe. Preserve the failed attempt. Native uncertainty is reconciled by
the existing owner before any remaining operation is executed.
