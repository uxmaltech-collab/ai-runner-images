# Changelog

Releases of this repository are tags `vX.Y.Z` on its default branch. The
publishable recipes and their versions are listed in
[`recipes/manifest.json`](recipes/manifest.json); a release publishes this
repository as one tree in the release repository (see Releasing in the README
for what the publisher does and does not read from the manifest). No built image
is ever part of a release.

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
  paths and the former emulator ownership marker are organization facts. A recipe takes
  them as build arguments that the planner resolves from the canon, declared under
  `inputs` in the manifest and applied by `recipes/collab-runners/common/plan-inputs.py`.
  The journey declarations keep their prior verified bindings, unchanged, as the
  fallback: with no value, or an incomplete or invalid set, the binding is kept and a
  warning is printed and returned, so the image stays what was verified, and no
  placeholder is ever written. The pinned runtime's own validation accepts the rendered
  and the shipped bindings (the tests run it when the runtime source is available).
- Helpers: the installed commands, the `/opt` paths and the environment variables that
  carried an organization prefix lose it. The Android helpers are the layer's
  `runner-android-emulator` and `runner-android-stack-probe`, and the web helpers are
  `runner-web-stack-install`, `-stack-probe`, `-playwright-mcp` and `-screenshot`; the
  manifest lists them by capability under `helpers`. The emulator wrapper exports the
  ownership marker `RUNNER_ANDROID_EMULATOR_OWNED` and, with the same value, each former
  marker name in `RUNNER_ANDROID_EMULATOR_OWNED_ALIASES`; `plan-inputs.py aliases` links
  each former helper path of the canon to its neutral helper without replacing a file.
- The Android layer is released once. `runner-resolver-android` builds `FROM` the
  image of the `android` recipe by digest (`RUNNER_ANDROID_IMAGE`, pinned by version
  in the manifest's `parent`) and no longer repeats the toolchain lock, the emulator
  registration, the helpers or the entrypoint.
- Provenance: the extraction records (`extraction.json`, `qa-extraction.json`,
  `recipes/android/extraction.json`) are unchanged. They hold the exact source
  repository, path, commit and digest, which belong to the organization; a shared
  repository cannot carry a reference to them without naming it, so moving them is the
  organization's change.
- Builds: the organization's console orders the build of an adopted recipe on its
  builder node and keeps the image in the console's registry; hosts pull by digest and
  never build. The previous route (`scripts/build-images.py` on the build host) stays
  valid until the organization's console has its registry.
- `uxmaltech-base-image`: the copy under `recipes/templates/` was an earlier state of
  the source of truth's Dockerfile, not a deliberate variant. It is replaced by a
  pointer to `containers/uxmaltech-base-image` in `uxmaltech-collab/ai-templates-resources`.
- Fixed: `compatibility/collab-image-recipes.lock.json` recorded stale bytes for three
  files; it is regenerated from the current recipe bytes (and follows the renames).
