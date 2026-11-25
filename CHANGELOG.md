# Changelog

Releases of this repository are tags `vX.Y.Z` on its default branch. The
publishable recipes and their versions are listed in
[`recipes/manifest.json`](recipes/manifest.json); a release publishes this
repository as one tree in the release repository (see Releasing in the README
for what the publisher does and does not read from the manifest). No built image
is ever part of a release.

## Unreleased

- `runner-resolver-php83` builds PHP with `--with-pdo-mysql` (bundled mysqlnd: no new build or
  runtime package), and its platform probe requires `pdo_mysql`. The CBQ package resolvers run
  their MySQL-backed tests with it; before, those tests could not open a MySQL connection.

- The resolver recipes (`runner-resolver-airflow-dag`, `-android`, `-ios`, `-mobile-qa`,
  `-nuxt-pnpm`, `-php-laravel`, `-php-mysql-redis`, `-php83`, `-web-qa`) no longer bake the
  Collab runtime: the `collab-release` copy and install, the `/opt/collab/runtime/bin` `PATH`
  entry, `ARCHIFY_PUBLISH_PYTHON` and the `collab --version` probe are removed; `python3.12`
  and the rest of each image stay. The manifest declares neither `context_inputs` nor
  `context` for them. At job start the control plane mounts the host's verified runtime
  read-only and exports `COLLAB_RUNTIME=<path>@sha256:<digest>`; a job with no host mount and
  no baked runtime warns and leaves the variable unset. The control-plane stack and the
  native macOS declarations are unchanged.

## 0.1.0

First release: the recipes as they stand, with the repository ordered for
publication.

- Recipes: a manifest, `recipes/manifest.json` (schema `collab.recipes-manifest/v1`;
  the former `uxmaltech-collab.*` spelling is still read, with one warning), lists
  each publishable Dockerfile recipe directory with its version: the Android layer
  and the Linux runner recipes of `recipes/collab-runners/`. Native macOS profiles are
  not OCI images and are not listed. `scripts/check-recipe-manifest.py` only warns
  (every finding, a missing or malformed manifest or changelog included, and a
  `--root` without its value) and always exits 0; it reads the manifest once.
- Identifiers name a stack, never a repository. The nine resolver recipes that carried
  a repository's name now carry the stack they install (`runner-resolver-android`,
  `-ios`, `-nuxt-pnpm`, `-web-qa`, `-mobile-qa`, `-php-laravel`, `-php-mysql-redis`,
  `-php83`); the two PHP 8.3 source-build recipes, identical but for their names, are
  one recipe. Which repository uses which recipe, and which engine, is organization
  data that the planner reads from the canon.
- Labels: the recipes that set image labels use the neutral namespace
  `collab.runner.*` (`profile`, `stack`) in place of an organization's
  `io.<organization>.runner.*`; no other organization's namespace replaces it. The
  `engine` label is gone: every engine is installed in the agent base and which one an
  agent runs is organization data. An organization that still reads a former
  namespace, its profile id or an engine declares the alias in its canon and the
  planner adds it with `--label`. The two base recipes keep the labels they had.
- Plan-time inputs: a journey's repository, profile and validator, the former helper
  paths and the former emulator ownership marker are organization facts, and so are the
  package registries (scope, host and the *name* of the credential variable) the web
  install helper needs, and the approved digest of the Android layer. A recipe takes
  them as build arguments that the planner resolves from the organization's canon,
  declared under `inputs` in the manifest and applied by
  `recipes/collab-runners/common/plan-inputs.py`. The journey declarations are templates:
  their constants, and `null` where an organization fact goes. With no value, or an
  incomplete or invalid set, no binding is written and the build goes on as the generic
  image with a warning: nothing is kept from, or invented for, any organization, and
  no placeholder is ever written. The pinned runtime's own validation accepts the
  rendered bindings (the tests run it when the runtime source is available).
- The pinned runtime launches the emulator helper with a fixed list of environment
  variables, so the former marker names reach it through an image-owned file
  (`/etc/runner-android-emulator/marker-aliases`) instead of the variable the image used
  to set. The web install helper reads its registry bindings from RUNNER_WEB_REGISTRIES
  or `/etc/runner-web-stack/registries`, names the credential variable of each binding
  (never a value), keeps the user's other npm settings, and warns instead of stopping
  when a variable is empty or nothing is declared.
- A parent image's reference spelling is only metadata, its digest is what is verified: the
  Dockerfiles that stopped a build because a reference was not written
  `<image>@sha256:<digest>` now warn. The Android resolver checks the digest of its
  reference (for a tag, the one the builder observed and passes as
  `RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST`) against the approved one (`plan-inputs.py
  parent`). It stops when a tag has no observed or no approved digest, and when the digest
  is not the approved one, because the bytes the build starts from would not be verified;
  an equal digest continues with a warning about the spelling. A digest-qualified reference
  with no approved digest only warns.
- The native iOS `image-build.json` is a template whose `driver` is `null`: the plan renders
  `journey-driver.json` first and `image-build.json` with `--driver <rendered driver>`, so the
  declaration points at the rendered driver, never at the template.
- `runner-base`'s `RUNNER_BASE_CONTEXT` defaults to a path the release tree holds
  (`recipes/collab-runners/runner-base`), and the manifest check resolves every `COPY`
  source of every recipe, with the `ARG` defaults applied, inside the recipe's path or its
  `shared` paths (`context_inputs` names what the builder supplies, such as
  `collab-release`).
- Every recipe declares its base as `parent` in the manifest, so no build takes it
  through an undeclared `ARG ... FROM ${...}`. A parent has three forms: a recipe of this
  manifest (`{recipe, version, build_arg}`: `runner-agent-base` and the `runner-ci-*`
  recipes on `runner-base`, the resolvers and the Android layer on `runner-agent-base`,
  `runner-resolver-android` on `android`); the image of a recipe of another released
  component (`{component, recipe?, version, build_arg}`, none used today); and an image no
  recipe builds, by a neutral profile the organization pins by digest under `image_pins`
  (`{pin, build_arg}`: `runner-base` on `runner-base-os`). No registry, tag or digest of
  any organization is in the manifest.
- The resolver recipes declare what fills `collab-release/` (`context`, in the shape of a
  container recipe's `version.json` `build.context`): the Collab runtime's release
  artifact set (`uxmaltech-collab/cli`, versions `>=0.2.3`); the version an organization
  runs is the one its console's adoption names, never a pin of the recipe. The runtime lock
  of this repository is the floor and the exact identity of its own version; a newer release
  is verified against its own lock (docs/build-images.md). The manifest
  check validates both additions, warns about a `context_inputs` name with nothing that
  fills it and about a `FROM ${ARG}` with no default that is not the parent's argument.
- Every build argument a Dockerfile stops without is mapped under `inputs`, so the
  console's builder can build every recipe of the manifest. An input is a fact key
  `<group>.<fact>`. The tool versions and digests that the recipes verify their
  downloads against are facts the organization declares under
  `recipe_inputs.<recipe name>` of its canon: `tools.*` (`runner-base`: the Actions
  runner, actionlint and the Docker CLI), `harness.*` (`runner-agent-base`: Claude Code,
  Codex CLI and Grok CLI) and `php.*` (`runner-resolver-php83`: the PHP source, the
  redis extension and Composer). Both arguments of an `_AMD64`/`_ARM64` pair are mapped,
  and the recipe keeps verifying every download against its digest. The source revision
  of an image (`RUNNER_SOURCE_COMMIT` of `android`, `AI_REPO_RESOURCES_BUNDLE_COMMIT` of
  the `runner-ci-*` recipes and the resolvers) is the reserved `release.commit`: the
  commit of the release whose tree is built. The console supplies it, and no
  organization declares it. The groups `release`, `context`, `builder` and `image_pins`
  are reserved. `docs/build-images.md` lists the keys of each recipe and who supplies
  each one. No value is in this repository.
- `scripts/check-recipe-manifest.py` warns about a build argument that has no default,
  that the Dockerfile requires (`test -n`, or the digest `sha256sum -c` reads, directly
  or through a shell variable), and that is neither mapped under `inputs` nor the
  parent's `build_arg`. It also warns about an input key that is not `<group>.<fact>`,
  or that belongs to a reserved group and is not a key that something supplies.
- `scripts/check-recipe-manifest.py` also compares each recipe with the previous release
  tag and warns about a recipe whose Dockerfile, copied sources or parent declaration
  changed without a version bump (it only warns); a parent that changes in any way (another
  recipe, a pin, a build argument) counts, not only its version.
- Helpers: the installed commands, the `/opt` paths and the environment variables that
  carried an organization prefix lose it. The Android helpers are the layer's
  `runner-android-emulator` and `runner-android-stack-probe`, and the web helpers are
  `runner-web-stack-install`, `-stack-probe`, `-playwright-mcp` and `-screenshot`; the
  manifest lists them by capability under `helpers`. The emulator wrapper exports the
  ownership marker `RUNNER_ANDROID_EMULATOR_OWNED` and, with the same value, each former
  marker name listed in the image-owned file or in `RUNNER_ANDROID_EMULATOR_OWNED_ALIASES`; `plan-inputs.py aliases` links
  each former helper path of the canon to its neutral helper without replacing a file.
- The Android layer is released once. `runner-resolver-android` builds `FROM` the
  image of the `android` recipe (`RUNNER_ANDROID_IMAGE`, pinned by version
  in the manifest's `parent`) and no longer repeats the toolchain lock, the emulator
  registration, the helpers or the entrypoint.
- Provenance: the extraction records (`extraction.json`, `qa-extraction.json`,
  `recipes/android/extraction.json`) are unchanged. They hold the exact source
  repository, path, commit and digest, which belong to the organization; a shared
  repository cannot carry a reference to them without naming it, so moving them is the
  organization's change.
- Builds: the organization's console orders the build of an adopted recipe on its
  builder node and keeps the image in the console's registry; hosts pull by digest and
  never build. Until it does, `scripts/build-images.py` builds and qualifies only the
  Android layer, the Linux control plane and the native macOS profiles; the resolver and
  CI recipes have no profile, and the build host builds them with Docker from the release
  tree as `docs/build-images.md` describes (unqualified: no `smoke.sh`, no backend).
- Release procedure: the README states what the publisher does today. It does not read
  `recipes/manifest.json`; it publishes this repository as one tree per version (no
  per-recipe component, no lookup by a recipe's name and version in the index, no
  `--path`), and ends at a local commit of the release repository that must be delivered
  there. Publishing each recipe under its own component is a change of that publisher
  and is not made.
- `uxmaltech-base-image`: the copy under `recipes/templates/` was an earlier state of
  the source of truth's Dockerfile, not a deliberate variant. It is replaced by a
  pointer to `containers/uxmaltech-base-image` in `uxmaltech-collab/ai-templates-resources`.
- Fixed: `compatibility/collab-image-recipes.lock.json` recorded stale bytes for three
  files; it is regenerated from the current recipe bytes (and follows the renames).
