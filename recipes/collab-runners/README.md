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
