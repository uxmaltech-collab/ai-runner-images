# Collab Python control-plane recipe

This recipe installs the exact `uxmaltech-collab/cli` wheel and its hash-locked
dependencies in an isolated environment. Runtime code is never copied from a
resource pack or Templates checkout. Mount the separately pinned declarative
Repo pack read-only at `/etc/collab/repo-pack`; its runtime lock must match the
installed release receipt. Credentials and host bindings remain external.

The build context contains this Dockerfile and `collab-release/`, the complete
verified release artifact set. The caller supplies immutable Python and runner-tool base
image digests, the recipe source commit and the exact CLI source commit as build
arguments. The installed private `collab_runners.controlplane` entrypoint owns the
HTTP service; it does not add a public runner-spawn command.

The release must use the version-two manifest and include the separately owned
`runners` provider. A base-only distribution is rejected before creating the
context; the copied artifact set is verified again before its receipt is written.
Git supports canonical source reads and OpenSSH supports the assigned native
executor transport. The recipe checks their presence and imports the installed
provider during the build. These checks do not register a runner or contact a
native host; actual image qualification and per-route canaries remain required.

Use `prepare.py` to verify the supplied source and artifact identities and create
a new build context. It performs no Docker build, image publication, host
installation or GitHub mutation. Existing qualified image tuples and historical
recipes remain unchanged until separately authorized build and promotion.

This candidate recipe has no built image identity or operational qualification.
Its final runtime lock is supplied from the reviewed Collab release artifact set;
there is no floating latest-version resolver or fabricated release digest.

Preparation validates the expected lock through the runtime's shared declarative
schema. Malformed locks, undeclared fields and invalid base image identities are
rejected before a context directory is created. Every copied artifact must retain
its verified digest, and the copied release is independently verified. A failed
copy keeps its partial directory for inspection without a success receipt; retry
uses a new directory and preserves that evidence.

The context receipt records the runtime, selected provider identities, release
manifest hash, expected lock hash, Dockerfile hash and both base image references
separately. Its file inventory describes exact prepared bytes; it does not claim a
recipe Git commit, a built image digest, installation or operational acceptance.
The supplied build arguments must still use the final reviewed recipe and runtime
commits, and image readback must verify those labels against the preparation.

Run isolated preparation checks with the candidate runtime available and an
explicit directory of offline release fixtures:

```console
PYTHONPATH=/path/to/cli/src COLLAB_TEST_RELEASES=/path/to/releases \
  python -m pytest -q stacks/collab-control-plane/test_prepare.py
```

The release fixture directory contains `base/`, `runners/` and `infra/` artifact
sets. Historical artifact fixtures exercise verification and copying only. They
do not qualify a new runtime or justify reuse of an earlier image digest.

Before publication, create a new recipe identity from the final reviewed commit,
update the candidate recipe inventory and runtime lock using that commit and the
newly verified release, build with the declared parent digests, and qualify the
resulting image on its actual routes. The current
`compatibility/collab-image-recipes.lock.json` selects the locally qualified
0.2.0 artifacts from CLI main commit `cf3cb8d35e96e4f89dd1f68b3014136447dc5562`.
It records current recipe bytes without claiming an image build. Historical
qualification records retain their original source and artifact identities.
