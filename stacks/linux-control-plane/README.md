# Portable Linux control plane and runner images

This recipe materializes the **existing** Templates engine; it does not fork a
second dispatcher or operator. The generated tenant owns its declaration,
catalog, Compose deployment and workflow. It has no EnviaFlores pack, credential,
host assignment or registry dependency.

The designated real test tenant is **[collab-e2e-org](https://github.com/collab-e2e-org)**,
created for cross-organization end-to-end qualification. Its runner canary uses
**[collab-delivery](https://github.com/collab-e2e-org/collab-delivery)**. These names
live in `qualification.json`, not in the reusable engine. The group's numeric
ID must be reconciled with that organization's actual group before deployment;
the example value `1` is not an assertion that the group grants repository access.

## Inputs and ownership

- `lock.json`: exact Templates commit, every consumed file digest, immutable
  root image references, tool archive checksums and combined harness versions.
- `requirements.lock` and `wheels.lock.json`: complete hash-locked CPython 3.12
  Linux amd64 control-plane Python dependency closure.
- `qualification.json`: tenant/repository identity, runner group, labels,
  image namespace and network. The materializer changes only the documented
  profile block interiors, retaining the shared core byte for byte.
- The four image outputs are runner-base, the combined three-agent base,
  the minimal CI leaf and control plane. Authenticated resolver operations,
  application builds, Android/KVM, browsers and native macOS are separate
  profiles/recipes and require their own canaries. This CI canary does not
  claim their acceptance.

Templates owns base image components and the engine. This repository owns the
reusable stack build and artifact qualification. Application consumers own
their CLI, workflows and flows. The `agents` Docker target deliberately omits
the pack CLI; the default `consumer` target keeps the existing pack CLI build.

## Materialize and build

Use a clean checkout containing the exact Templates commit in the lock. The
materializer reads committed objects, not modified worktree bytes. Use separate
new output directories; comparing their `MATERIALIZATION.json` proves the same
declared inputs render the same source tree.

```sh
python3 stacks/linux-control-plane/materialize.py \
  --templates /path/to/ai-templates-resources \
  --declaration stacks/linux-control-plane/qualification.json --output /private/pack
python3.12 stacks/linux-control-plane/build.py \
  --pack /private/pack --evidence /private/build-evidence --download-wheels
```

Provide the two digest-qualified root images first. The builder refuses missing
roots instead of silently pulling them. It consumes no GitHub or agent secrets,
retains separate command/build logs and probes all three harnesses without
network access as UID 1001. It records installed OS packages and saves all four
images in `images.tar`, with exact size, SHA-256 and immutable references in
`BUILD.json`. Keep that large archive outside Git in the approved artifact
store; retaining only the receipt or a local tag is insufficient for recovery.

**Reproducibility limits:** rendering and Python wheels are fully locked.
Canonical runner-base still resolves APT packages from live repositories and
the agent stage uses npm resolution. A source rebuild is not promised to be
bit-identical. Preserve and restore the verified image archive for exact bytes;
qualify a rebuild as a new artifact and compare its inventories. Upstream
archive or installer changes must fail their hash check, never silently advance
a pin. ARM64 is not covered by this amd64 wheel lock.

To prove cold restoration on a Linux host, run the disposable rehearsal with
root, Docker and containerd available:

```sh
python3 stacks/linux-control-plane/restore-rehearsal.py \
  --build-receipt /private/build-evidence/BUILD.json \
  --declaration /private/pack/declaration.json --evidence /private/restore-evidence
```

It verifies the archive before import, uses new data roots **and a separate
containerd socket/namespace and private Linux network namespace**, checks an empty image store, imports all images,
compares immutable references and layers, runs unprivileged tool probes and
boots the real control-plane application without credentials or network access.
The control-plane's GitHub queue reader is disabled only for this offline
rehearsal. It never mounts a production Docker socket. Both test daemons and
the test control plane are stopped; logs and `RESTORE.json` retain failures
and cleanup. An isolated data root alone does not isolate a system containerd;
`--bridge none` alone does not protect the host's existing network links.

## Runtime and real GitHub acceptance

Use a separate GitHub App owned by `collab-e2e-org`, installed only on the test
repository. For the CI path it needs repository Actions read, Metadata read,
and organization Self-hosted runners write. No OAuth client secret, EnviaFlores
App, personal access token or agent seed belongs in this stack. Keep the PEM
private on the runtime host and mount it only into the control plane. The job
gets GitHub's ephemeral JIT credential; it gets neither the App key nor the
Docker socket. The queue reader permits operation without a public webhook.

Deploy through the host's assigned owner. The generated `compose.yaml` requires
explicit immutable image digests, a private App metadata file and key path,
an assigned Docker socket and an unused loopback port. It declares its own
network and state volume. Do not reuse an installed production project's name,
state, socket authority or namespaces without its owner's assignment.

Publish the generated workflow in the test repository, then dispatch **once**
after group access, App identity and permissions are verified. Retain the
workflow/source SHA, image digest, run/job IDs, terminal result and removal of
the ephemeral runner/container. A second organization's successful run proves
this CI path only. A health response, simulated event or tool version does not
prove GitHub dispatch, agent authentication or a mobile journey.

Record `not-run` while real GitHub authority is unavailable. Never use a PAT
fallback or weaken the App authorization contract to make a local test pass.
