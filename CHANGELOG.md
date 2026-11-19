# Changelog

Releases of this repository are tags `vX.Y.Z` on its default branch. The
publishable recipes and their versions are listed in
[`recipes/manifest.json`](recipes/manifest.json); a release publishes their trees
in `uxmaltech-collab/releases` (see Releasing in the README). No built image is
ever part of a release.

## 0.1.0

First release: the recipes as they stand, with the repository ordered for
publication.

- Recipes: a manifest, `recipes/manifest.json`, lists each publishable Dockerfile
  recipe directory with its version (the Android layer and the Linux runner recipes
  of `recipes/collab-runners/`), so the release repository's publish command can
  find them. Native macOS profiles are not OCI images and are not listed.
- Builds: the organization's console orders the build of an adopted recipe on its
  builder node and keeps the image in the console's registry; hosts pull by digest
  and never build. The previous route (`scripts/build-images.py` on the build host)
  stays valid until the organization's console has its registry.
- Provenance: the runner recipes keep their extraction records, now naming the
  source as "an organization pack" with its commit. No recipe, label, installed
  command or example binding names an organization any more. This renames, in the
  recipes that were not yet built or promoted: the label namespace
  `io.<organization>.runner.*` becomes `io.uxmaltech.runner.*`; the installed
  commands, scripts and `/opt` paths that carried an organization prefix lose it
  (`storefront-android-emulator`, `storefront-android-stack-probe`,
  `storefront-web-*`, `/opt/storefront-android`, `/opt/storefront-web-*`); the
  environment variables `STOREFRONT_WEB_STACK_PROBE` and `ANDROID_EMULATOR_OWNED`
  lose their prefix; the repository fields of the journey declarations are
  `<organization>/<repository>` placeholders; and the recipe
  `runner-resolver-last-mile-core-pkg` is now `runner-resolver-backoffice-core-pkg`.
- `uxmaltech-base-image`: the copy under `recipes/templates/` was an earlier state of
  the source of truth's Dockerfile, not a deliberate variant. It is replaced by a
  pointer to `containers/uxmaltech-base-image` in `uxmaltech-collab/ai-templates-resources`.
- Fixed: `compatibility/collab-image-recipes.lock.json` recorded stale bytes for three
  files; it is regenerated from the current recipe bytes (and follows the renames).
