# Collab runner recipe adoption

These current Linux toolchain recipes were extracted from an organization pack
(its commit and the digest of each source file are recorded in extraction.json;
the pack's identity is not kept). The combined agent base carries the technology stack only.
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
Before preparing a build context, verify the complete offline release against
that runtime identity and verify every recipe file digest. The release is
provided separately; it is never resolved through a floating version.

## Release and builds

Each directory here is a recipe listed in [`../manifest.json`](../manifest.json)
with its version, and a release of this repository publishes its tree in
`uxmaltech-collab/releases` (see Releasing in the root README). The recipe is what
is released; the image is not. The organization's console orders the build on its
builder node and keeps the image in the console's registry
(`<console registry name>/<image>@sha256:<digest>`); a flavor builds
`FROM <console registry name>/runner-agent-base@sha256:<digest>` and hosts pull by
digest and never build. The builder labels the image with `collab.recipe.component`,
`collab.recipe.version`, `collab.recipe.tree_digest` and `collab.build.id` (it
passes them to `docker build` with `--label`; the Dockerfiles do not set them).
These recipes have no `smoke.sh` yet; the build is qualified through
`scripts/build-images.py`.

**Transition.** The console route does not exist yet. Until the organization's
console has its registry and a builder node, the previous route stays valid: build
on the build host as [docs/build-images.md](../../docs/build-images.md) describes
and pin the digest of the image in the registry the organization already uses.

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
