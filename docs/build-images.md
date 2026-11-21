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
   the exact release as `collab-release/` at the root of the context, verified first.
   The selection and the verification read the same declarations.
   [`compatibility/collab-runtime.lock.json`](../compatibility/collab-runtime.lock.json)
   is the floor of the selection (`>=` its `runtime.version`) and the exact identity of
   that version: when the selected release is that version, its `collab-runtime.lock.json`,
   its wheel name, wheel SHA-256 and commit must equal the lock's, byte for byte. A newer
   selected release is not this lock's identity, so it is verified against its own
   `collab-runtime.lock.json` (same `runtime.repository`, a `runtime.version` that is the
   selected version and not older than the floor, a wheel whose SHA-256 is the one that
   lock names and its `SHA256SUMS` lists); a mismatch stops the build, and this
   repository holds no qualification evidence for a newer release.
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
   argument. The reference is always digest-qualified, `<image>@sha256:<digest>`: a tag is
   mutable, so it is resolved to its digest first and the digest-qualified reference is
   what the build uses (the console's builder does this). A Dockerfile whose base is a
   tag stops, as it does on `main`. Verify the parent against the approved digest (the
   organization's image pin):

   ```sh
   docker image inspect --format '{{index .RepoDigests 0}}' <parent image>   # the digest to build from
   python3 recipes/collab-runners/common/plan-inputs.py parent \
     --reference <image>@sha256:<digest> --approved sha256:<approved>
   ```

   The command stops (exit 1) when the reference is a tag, and when its digest is not the
   approved one: that image is another artifact. With no approved digest it warns that the
   parent is unverified and goes on. `--resolved` is an optional cross-check of the digest
   the builder observed; a difference only warns. The same check runs inside the build of
   `runner-resolver-android` (`RUNNER_ANDROID_IMAGE_DIGEST`,
   `RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST`).
3. **Plan-time inputs.** Each fact is a `--build-arg` named under `inputs` in the
   manifest, which maps the argument to a fact key `<group>.<fact>`; the values never
   come from this repository. See [Recipe inputs](#recipe-inputs) for the keys of each
   recipe and who supplies each one.
4. **Build.**

   ```sh
   docker build -f recipes/collab-runners/runner-resolver-android/Dockerfile \
     --build-arg RUNNER_ANDROID_IMAGE=<image>@sha256:<digest> \
     --build-arg RUNNER_ANDROID_IMAGE_DIGEST=sha256:<approved> \
     --build-arg <input>=<value> ... -t <image> .
   ```

   The builder labels the image with `collab.recipe.component`, `collab.recipe.version`,
   `collab.recipe.tree_digest` and `collab.build.id` (`--label`), and records the digest
   of the result for the registry the organization already uses.

## Recipe inputs

Every build argument a recipe takes from outside is mapped under `inputs` in
[`recipes/manifest.json`](../recipes/manifest.json) to a fact key `<group>.<fact>`. The
keys come from two places:

- **The organization's declaration.** The organization declares the value of a key
  under `recipe_inputs.<recipe name>.<group>.<fact>` of its canon declaration
  (`governance/release-adoption.yaml`): a string, or a list of strings. Its console
  passes it with the build. The groups are named after a tool family, and each key
  is `<tool>_version` or `<tool>_sha256`, with `_amd64` or `_arm64` added when the
  digest differs per architecture:
  - `tools`: the runner tools of `runner-base` (`actions_runner`, `actionlint`,
    `docker_cli`);
  - `harness`: the agent harnesses of `runner-agent-base` (`claude_code`, `codex_cli`,
    `grok_cli`), the versions of the harness pins the organization adopted;
  - `php`: the PHP 8.3 build of `runner-resolver-php83` (`php`: the source tarball,
    `redis`: the PECL redis extension, `composer`: the PHAR);
  - `journey`, `helper`, `web`: the bindings of an organization's journeys, its former
    helper names and its package registries (see
    [Plan-time inputs](../recipes/collab-runners/README.md#plan-time-inputs)).

  A `*_sha256` value is the SHA-256 hex digest of the exact file the recipe downloads.
  The recipe keeps verifying the download against it (`sha256sum -c`), so a digest that
  is not the file's stops the build inside the recipe: that file is another artifact.
  A version and its digests go together. A `*_version` key that is not declared keeps
  the Dockerfile's default, so the digests declared must be the ones for that default.
  Both keys of an `_amd64`/`_arm64` pair are declared and both are passed; the
  Dockerfile picks the one for `TARGETARCH`.
- **Reserved groups, never declared.** `release`, `context`, `builder` and `image_pins`
  are filled from what is already verified. A declared key of one of these groups is
  left out with a warning, by the console and by the builder:
  - `release.commit`: the commit of the release whose tree is built, as the release
    index row gives it (its `commit`, else its `tag_commit`). The console holds it
    with the stored tree and sends it with the build. It is the source revision of the
    image (`RUNNER_SOURCE_COMMIT`, `AI_REPO_RESOURCES_BUNDLE_COMMIT`). A recipe that
    requires it and gets none (the console holds no exact commit for that release)
    stops at its own `test -n`; nothing invents one.
  - `image_pins.digest`: the digest of the parent the build record pins;
    `builder.resolved_parent_digest`: what the builder observes for the pulled parent (an optional cross-check).
  - `context` is reserved for facts of a resolved context entry; none is supplied yet.

"Required" below means that the Dockerfile has no default for the argument and stops
without it. "Optional" means that the recipe builds its generic image, or uses the
Dockerfile's default, without it. `scripts/check-recipe-manifest.py` warns about a
required argument that is neither mapped under `inputs` nor the parent's `build_arg`.

| Recipe | Required: the organization declares | Optional: the organization may declare | Supplied, never declared |
| --- | --- | --- | --- |
| `android` | none | none | `release.commit` |
| `collab-runners-runner-agent-base` | `harness.claude_code_version`, `harness.codex_cli_version`, `harness.grok_cli_sha256_amd64`, `harness.grok_cli_sha256_arm64`, `harness.grok_cli_version` | none | none |
| `collab-runners-runner-base` | `tools.actionlint_sha256_amd64`, `tools.actionlint_sha256_arm64`, `tools.actions_runner_sha256_amd64`, `tools.actions_runner_sha256_arm64`, `tools.docker_cli_sha256_amd64`, `tools.docker_cli_sha256_arm64` | `tools.actionlint_version`, `tools.actions_runner_version`, `tools.docker_cli_version` | none |
| `collab-runners-runner-ci-ai-resources` | none | none | `release.commit` |
| `collab-runners-runner-ci-airflow-dag` | none | none | `release.commit` |
| `collab-runners-runner-ci-php-laravel` | none | none | `release.commit` |
| `collab-runners-runner-ci-web-e2e` | none | none | `release.commit` |
| `collab-runners-runner-resolver-airflow-dag` | none | none | `release.commit` |
| `collab-runners-runner-resolver-android` | none | `helper.aliases`, `helper.marker_aliases`, `journey.profile`, `journey.repository`, `journey.validator` | `builder.resolved_parent_digest`, `image_pins.digest`, `release.commit` |
| `collab-runners-runner-resolver-ios` | none | none | `release.commit` |
| `collab-runners-runner-resolver-mobile-qa` | none | none | `release.commit` |
| `collab-runners-runner-resolver-nuxt-pnpm` | none | `helper.aliases`, `web.registries` | `release.commit` |
| `collab-runners-runner-resolver-php-laravel` | none | none | `release.commit` |
| `collab-runners-runner-resolver-php-mysql-redis` | none | none | `release.commit` |
| `collab-runners-runner-resolver-php83` | `php.composer_sha256`, `php.php_sha256`, `php.redis_sha256` | `php.composer_version`, `php.php_version`, `php.redis_version` | `release.commit` |
| `collab-runners-runner-resolver-web-qa` | none | none | `release.commit` |

`release.commit` is required by `android` and the four `runner-ci-*` recipes, which
stop without it. The resolvers only use it to label the image's revision.

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
