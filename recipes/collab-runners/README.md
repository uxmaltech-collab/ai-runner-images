# Collab runner recipe adoption

These current Linux toolchain recipes were extracted from an organization pack.
The exact source repository, path, commit and digest of each source file are
recorded in `extraction.json`, `qa-extraction.json` and
[`../android/extraction.json`](../android/extraction.json), as they were extracted.
That provenance belongs to the organization: the records are kept untouched here,
because a shared repository cannot carry a resolvable reference to it without
naming the organization, and moving it behind a reference the organization owns is
the organization's change (no location is invented here). Their `destination` and
recipe paths are the paths of the extraction: the recipe directories that carried a
repository's name were renamed to the stack they install, and the Android inputs
that the resolver repeated were removed in favor of the layer that owns them
(`git log --follow <path>` finds a former path). The combined agent base carries the technology stack only.
Every leaf image installs one exact Collab release, prepared as `collab-release`
in the build context, as its last layer, and declares the arguments that change
with every publication (its parent digest and the pack revision) only after the
stack layers, so a Collab release rebuilds one layer per leaf on top of the
cached stack. No resource package supplies
executable code or a local CLI. Browser and agent toolchains remain external
dependencies with their existing pins. No image has been built or promoted by
this change. Recipes require their own Linux qualification after adoption.

The reviewed source uses [the exact runtime lock](../../compatibility/collab-runtime.lock.json)
and [the recipe file manifest](../../compatibility/collab-image-recipes.lock.json).
Before preparing a build context, verify the complete offline release and verify
every recipe file digest. The release is provided separately, and an exact release
is verified, never a range: the lock above is the floor (`>=` its version) of what a
console may select and the exact identity of that version; a newer selected release is
verified against its own runtime lock and digests, and carries no qualification
evidence from this repository (see Resolver and CI recipes in
[`docs/build-images.md`](../../docs/build-images.md)).

## Release and builds

Each directory here is a recipe listed in [`../manifest.json`](../manifest.json)
with its version; a release of this repository publishes them as one tree (see
Releasing in the root README for what the publisher does). The recipe is what is
released; the image is not. The organization's console orders the build on its
builder node and keeps the image in the console's registry
(`<console registry name>/<image>@sha256:<digest>`); a flavor builds
`FROM <console registry name>/runner-agent-base@sha256:<digest>` and hosts pull by
digest and never build. The builder labels the image with `collab.recipe.component`,
`collab.recipe.version`, `collab.recipe.tree_digest` and `collab.build.id` (it
passes them to `docker build` with `--label`; the Dockerfiles do not set them).
These recipes have no `smoke.sh` yet, and `scripts/build-images.py` has no profile
that builds or qualifies them (only the Android layer and the Linux control plane): they
are not qualified by any script of this repository.

**Transition.** The console route does not exist yet. Until the organization's
console has its registry and a builder node, a build host builds a recipe with Docker from
the release tree as [Resolver and CI recipes](../../docs/build-images.md#resolver-and-ci-recipes)
describes, and pins the digest of the image in the registry the organization already uses.
The context of every recipe is the release tree: `RUNNER_BASE_CONTEXT` of
`runner-base` defaults to its own path in it, and the exact Collab release is
`collab-release/` at the root (`context_inputs` in the manifest; the entry's `context`
says it is the Collab runtime's release artifact set, and the console fills it with the
version the organization's adoption names).

Each recipe declares its base as `parent` in the manifest: `runner-agent-base` and the
`runner-ci-*` recipes start from `runner-base`; the `runner-resolver-*` recipes and the
Android layer start from `runner-agent-base` (it carries the Python 3.12 the leaf's
Collab install runs with); `runner-resolver-android` starts from the Android layer.
`runner-base` starts from an operating-system image that no recipe builds: its parent is
the neutral pin `runner-base-os`, which the organization pins by digest under
`image_pins` in its canon; without that pin the console defers the build.

### Identifiers name a stack

A release identifier (`name` in the manifest, the image title and the
`collab.runner.profile` label) names a toolchain, never a repository:

| Recipe directory | Toolchain |
| --- | --- |
| `runner-resolver-android` | the neutral Android layer (`../android`, released once) plus the journey binding, helper aliases and the Collab runtime |
| `runner-resolver-ios` | Linux resolver with SwiftLint; the native macOS image is not an OCI image |
| `runner-resolver-nuxt-pnpm` | Node, pnpm through Corepack, Playwright and its MCP |
| `runner-resolver-web-qa`, `runner-resolver-mobile-qa` | the agent base and the Collab runtime, for QA |
| `runner-resolver-php-laravel`, `runner-resolver-php-mysql-redis` | PHP from the distribution with Composer and Redis (the first adds GD and PostgreSQL) |
| `runner-resolver-php83` | PHP 8.3 built from source with Redis, Composer and GD with WebP (one recipe; every repository that needs it uses it) |
| `runner-resolver-airflow-dag`, `runner-ci-*` | their stacks, as named |

Which repository uses which recipe, and which engine, is organization data declared
in the organization's canon and resolved by the planner at plan time. Nothing here
maps a repository to a recipe or selects an engine for one.

The image labels use the neutral namespace `collab.runner.*` (`profile` and `stack`).
All three engines are installed together in the agent base, so no recipe selects
one: which engine a repository's agent runs is organization data, and a recipe
carries no `engine` label. An organization that still filters or reads a former label
namespace, its own profile id or an engine, declares that alias in its canon and the
planner adds it with `--label` at build time, exactly as the builder adds
`collab.recipe.*`; no recipe carries a former namespace. (The two base recipes keep
the labels they already had.)

### Plan-time inputs

Facts that belong to an organization reach a recipe only as build arguments that the
planner resolves from the organization's canon (or, when the canon cannot be read, from
the planner's own last verified read of it). Each recipe lists the arguments it takes, and
the fact each carries, under `inputs` in the manifest, and declares each as an `ARG`
(`scripts/check-recipe-manifest.py` warns when they differ). The facts are read from the
one declaration the owner names for them: `governance/release-adoption.yaml` of the
organization canon, until the owner says they live in an existing one; the fact names in
the manifest (`journey.repository`, `helper.aliases`, `web.registries`, ...) are the
planner's keys, never values. The tool versions and digests that `runner-base`,
`runner-agent-base` and `runner-resolver-php83` verify their downloads against are inputs
too (`tools.*`, `harness.*`, `php.*`), and the source revision of every image is the
reserved `release.commit`, which the console supplies and no organization declares: the
[table of recipe inputs](../../docs/build-images.md#recipe-inputs) lists, for each recipe,
the keys the organization declares and the ones it never does.
[`common/plan-inputs.py`](common/plan-inputs.py) applies
them and never stops a build, except for a parent image that is another artifact than the
approved one:

- `journey`: renders a journey binding (`repository`, `profile`, `validator`) from the
  recipe's template when all the facts the template binds are given and valid. A template
  is a document with its constants and `null` where an organization fact goes; no recipe
  carries a binding. With none, or a partial or invalid set, **nothing is written**, a
  warning is printed and returned (`status: not_done`), and the build goes on as the
  generic image: no value is invented and none is kept from another organization, and the
  pinned runtime, which compares the binding field by field with the pack's own
  declaration, finds none.
- `aliases`: links each `ALIAS=TARGET` pair (absolute paths under `/usr/local`) to the
  neutral helper, never replacing an existing file. This keeps a former helper path
  working while a consumer migrates; the former name comes from the canon, not from
  this repository.
- `markers`: writes the former emulator ownership-marker names to the image-owned file
  `/etc/runner-android-emulator/marker-aliases`. The pinned runtime starts the emulator
  helper with a fixed list of environment variables and drops the variable the image
  used to set, so the list travels in the file; the variable stays an explicit override.
- `registries`: writes the package registry bindings
  (`<scope>=<host>[=<credential variable name>]`) to `/etc/runner-web-stack/registries`,
  which `runner-web-stack-install` reads (it also reads them from
  `RUNNER_WEB_REGISTRIES` at run time). A binding names the variable that holds a
  credential, never a value. With none declared the helper changes no npm configuration
  and warns.
- `parent`: compares the digest the parent reference resolves to with the approved one.
  The reference must be digest-qualified: a tag is mutable and stops, as it does on
  `main`; no approved digest leaves the parent `unverified`, with a warning; a different
  digest stops.

The stable neutral helpers are listed under `helpers` in the manifest, by capability
(for example `android.emulator-owner`: `/usr/local/bin/runner-android-emulator`).

The declarations `runner-resolver-android/journey-driver.json`,
`runner-resolver-ios/journey-driver.json`, `runner-resolver-ios/journey-execution.json`
and `runner-resolver-ios/image-build.json` are **templates**: their organization facts
(`repository`, `profile`, `validator`, and `driver` in `image-build.json`) are `null` and
only their constants are shipped. The native iOS image is prepared by the organization's
planner: it renders the files from the facts it resolved with `plan-inputs.py journey
--template <the file here> --output <the plan's file>`, which writes nothing and warns
when it has no values. The image declaration `image-build.json` carries `driver: null`
because it must point at the driver document the plan rendered, not at the template:
render `journey-driver.json` first, then render `image-build.json` with `--driver <the
rendered driver file>`; the native preparation follows that path. Run
`PYTHONPATH=<cli>/src:<cli>/providers/runners/src python3 -m pytest -q recipes/collab-runners/common`
with the pinned runtime source to also check the rendered bindings with the runtime's own
validation (the tests skip without it).

The native iOS recipe uses schema-two image declarations. Its installed
preparation and image installer modules compose a sealed declarative Repo export
with a separate verified runtime tree. The image-owned journey supervisor selects
`repo.journey.ios.v2`; no entrypoint resides inside the exported pack. Existing
application validators remain in their application repositories. Recipe and
runtime pins do not qualify the image, admit a guest, or promote a host.

The selected runtime is `uxmaltech-collab==0.2.3` from CLI main commit
`63c60623eb3cd267f9ec06f252498b821740599a`. Its base, runners and Infra
provider wheels were built and installed offline on Linux amd64. The recipe
lock binds the full Infra bundle, which supplies every declared provider.
The exact artifacts are published in [Collab v0.2.3](https://github.com/uxmaltech-collab/cli/releases/tag/v0.2.3).
Native qualification, image construction and operational canaries remain pending.
The native preparation and installer identifiers belong to `collab_infra`;
the base wheel does not contain host implementations.

The Web QA and Mobile QA leaf recipes preserve the two additional profiles
already declared in the resource catalog. Their independent source provenance
is recorded in [qa-extraction.json](qa-extraction.json); the original extraction
record remains unchanged. Both inherit the same combined agent base and
Collab 0.2.3 runtime. The Mobile QA recipe is a Linux resolver, not a native
mobile build or journey qualification. These source recipes do not establish
that either route has an installed image or a successful canary.
