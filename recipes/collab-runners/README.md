# Collab runner recipe adoption

These current Linux toolchain recipes were extracted from the source recorded in
extraction.json. The combined agent base consumes one exact Collab release
prepared as `collab-release` in the build context. No resource package supplies
executable code or a local CLI. Browser and agent toolchains remain external
dependencies with their existing pins. No image has been built or promoted by
this change. Recipes require their own Linux qualification after adoption.

The reviewed source uses [the exact runtime lock](../../compatibility/collab-runtime.lock.json)
and [the recipe file manifest](../../compatibility/collab-image-recipes.lock.json).
Before preparing a build context, verify the complete offline release against
that runtime identity and verify every recipe file digest. The release is
provided separately; it is never resolved through a floating version.

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
