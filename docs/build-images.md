# Build images from their source of truth

Run the Python entrypoint in this repository. Local image storage is supported;
a remote registry or backup bucket is not a prerequisite. Preserve original
artifacts and receipts. This builds and qualifies images, without admitting them
into an executor or deploying a control plane.

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

## Native composition contract

The backend interface is `build(inputs, work, root, commit, *, profile)` and
returns a JSON-serializable result with `status`, artifacts, qualification and
cleanup references. `root` is the committed image SoT; `work` is a new private
directory. The frontend calls only the profile's fixed backend.

The native backend uses `scripts/tart-layer.py` and the existing image/session
owners to compose macOS/Xcode/Maestro, the combined Codex/Claude/Grok layer, then
optional Flutter/Dart. Inputs declare the parent tuple, tool payloads and host
binding; no host identity or private endpoint is baked into a recipe. Document
how to obtain the licensed macOS/Xcode parent and which retained artifacts are
still prerequisites. A retained parent does not establish a clean-machine build.

Qualification runs in a disposable nonadministrator guest session. Normal
shutdown and stopped config/disk/NVRAM hashes bind the output. Preserve accepted
images and use a derivative for changed components. SwiftLint and CLI relocation
must be recipe inputs/steps, not checkpoint-only repairs. The generic Python
console relocation recipe is in `recipes/python-runtime`; the consumer owns its
package name, entry point and final destination.

## Recovering a failed attempt

Read `RESULT.json`, component logs and completed receipts first. Do not overwrite
the work directory or blindly repeat native lifecycle operations. Reuse a verified
parent receipt for an unchanged Linux parent and start a new derived build for a
changed recipe. Preserve the failed attempt. Native uncertainty is reconciled by
the existing owner before any remaining operation is executed.
