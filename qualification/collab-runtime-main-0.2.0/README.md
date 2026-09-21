# Collab main runtime qualification for image recipes

CLI main commit `cf3cb8d35e96e4f89dd1f68b3014136447dc5562` (PRs 93, 94 and 95)
produced the separate base, runners and Infra wheels at version `0.2.0`.
The source tree is `5e3baeddbd661978bd2c9915553f8c65ec9c18e9`.

On Linux amd64 with Python 3.12.3, the offline build, three isolated profile
installations and eleven installed observations passed. The verifier checked
wheel source bytes and provenance, dependency closure, one public `collab`
entrypoint, provider boundaries and retained installation bytes. All 1,318
recorded qualification inputs remained unchanged.

The control-plane preparation suite passed 22 cases with zero failures, errors
or skips using these exact artifact bundles. It covers malformed and drifting
inputs, partial copies, provider selection and the installed control-plane
module. The added native recipe contract checks both preparation and installer
module paths inside the verified Infra wheel. Synthetic base image identities
in those tests do not identify or qualify any image.

[SUMMARY.json](SUMMARY.json) binds the observed results, artifacts and receipts.
The accompanying full Infra manifest supplies the base and runners profile
closures without rebuilding wheels. Its dependency wheels were selected for
Linux amd64; this directory contains evidence, not an installable release.

The first local source preparation was rejected because it used an alternate
object store with unavailable objects. A separate complete GitHub checkout was
then obtained, and the source guard and build passed without bypasses. Earlier
failed attempts and all historical artifacts remain in the retained task evidence.

Final release publication, macOS/arm64 qualification, image builds, adoption,
per-repository canaries and target recovery are pending. No image tuple, host
assignment, admission setting or operational receipt was replaced by this change.
