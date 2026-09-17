# Linux control-plane portability qualification

The designated test tenant is `collab-e2e-org`, with `collab-delivery` as the
real GitHub canary target. The [summary](SUMMARY.json) binds the consumed
Templates payload, four image identities, verified archive and local evidence.

The images were built without another consumer pack, staging environment,
App key or authenticated agent seed. A second empty Docker/containerd store
restored all immutable references and layers; the three harnesses ran offline
as UID 1001, and the real control-plane application passed local health.
Owned test processes stopped and no test containers remained.

The failed attempts are retained, including a network-isolation defect in the
first rehearsal. Its affected default bridge was restored with explicit
operator authorization; three original endpoints reached their gateway and
the production control plane stayed healthy without restarts. The corrected
rehearsal uses a private Linux network namespace in addition to independent
Docker/containerd roots, sockets and namespaces. Raw host receipts remain
private. A new data root or `--bridge none` is not a network isolation boundary.

The dedicated GitHub App and target access passed their preflight. **The real
GitHub dispatch is not yet recorded**, so no E2E acceptance is claimed here.
This Linux CI path does not credit Android, native macOS, authenticated agent
execution or application journeys. Exact archive restoration is proven on a
new local store; remote artifact distribution and bit-identical APT/npm source
rebuilds are not claimed.
