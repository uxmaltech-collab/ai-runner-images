# Collab Python control-plane recipe

This recipe installs the exact `uxmaltech-collab/cli` wheel and its hash-locked
dependencies in an isolated environment. Runtime code is never copied from a
resource pack or Templates checkout. Mount the separately pinned declarative
Repo pack read-only at `/etc/collab/repo-pack`; its runtime lock must match the
installed release receipt. Credentials and host bindings remain external.

The build context contains this Dockerfile and `collab-release/`, the complete
verified release artifact set. The caller supplies immutable Python and runner-tool base
image digests, the recipe source commit and the exact CLI source commit as build
arguments. The installed private `collab.repo.controlplane` entrypoint owns the
HTTP service; it does not add a public runner-spawn command.

Use `prepare.py` to verify the supplied source and artifact identities and create
a new build context. It performs no Docker build, image publication, host
installation or GitHub mutation. Existing qualified image tuples and historical
recipes remain unchanged until separately authorized build and promotion.

This candidate recipe has no built image identity or operational qualification.
Its final runtime lock is supplied from the reviewed Collab release artifact set;
there is no floating latest-version resolver or fabricated release digest.
