# GitHub runner research and development decisions

Primary documentation checked on 2026-09-23. The decisions below are our
operating design, not requirements attributed to GitHub or Tart.

## Read first when resuming a failed attempt

Restore the current task scope, owner AGENTS, selected runtime/recipe/pack,
last operation, attempt count and first error. Then select just the relevant
reference below; do not repeat inventory or browse every topic on each retry.

| Stage | Official reference |
| --- | --- |
| Routing and ephemeral lifecycle | [Self-hosted runners](https://docs.github.com/en/actions/reference/runners/self-hosted-runners) |
| JIT registration and permission scope | [Runner REST API](https://docs.github.com/en/rest/actions/self-hosted-runners#create-configuration-for-a-just-in-time-runner-for-a-repository) |
| Webhook delivery and job state | [workflow_job payload](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_job) |
| Listener, network and job failures | [Runner troubleshooting](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/monitor-and-troubleshoot) |
| Quota and request pacing | [REST best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api) |
| Native VM mechanics | [Tart quick start](https://tart.run/quick-start/) and [Tart source](https://github.com/cirruslabs/tart) |

Use the installed version's source for implementation questions. Follow this
with the local owner entrypoint/contract, then a changed hypothesis and the
smallest real execution that can confirm or refute it.

## Separate provisioning, execution and acceptance

GitHub routes a job by matching runner labels/groups and availability. A job
can remain queued while no matching runner exists. Thus absence from the current
runner list does not establish that a configured ephemeral route is disabled.
GitHub recommends ephemeral runners for autoscaling: a runner receives one job
and is deregistered afterward. Our infrastructure still owns VM/process cleanup.
See [self-hosted runners](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).

Decision: test image mechanics locally without treating a fake registration as
JIT. Exercise central registration/routing with an actual request on the assigned
path; correlate that job to the native execution and required delivery. Neither
a local tool check nor an idle online runner proves this integration.

## Diagnose the first real failure

GitHub documents `Runner_` logs for the listener and `Worker_` logs per job in
`_diag`, and recommends preserving ephemeral logs outside the disappearing
runner. Its connection check diagnoses service reachability, not job execution.
See [monitoring and troubleshooting](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/monitor-and-troubleshoot).

Decision: retain sanitized listener/job logs plus the native owner's process,
VM and application output before cleanup. Distinguish queue/routing, credentials,
network, runtime/pack, toolchain, engine and output/cleanup failures. Do not fix a
workflow merely because the visible error surfaced there. After three failed
attempts, investigate primary sources and the actual failing boundary before
trying a materially justified correction. No extra report approval is required.

## Test the native image without a central conversation loop

Tart exposes clone/run and guest execution/artifact retrieval; this supports a
disposable native test loop independently of GitHub job registration. See
[Tart quick start](https://tart.run/quick-start/). This does not authorize raw
host commands where our installed image/session owner is required.

Decision: the Mac owns the complete applicable mechanical sequence in
[native development](native-development.md), from clone and actual job-user
context through runtime/pack execution, neutral stack output and cleanup.
Linux provides central-only services when a real JIT boundary is exercised.
The existing historical session/SwiftLint qualifier covers only part of this
sequence. A reusable fixture using the current Collab entrypoint remains work
to implement; these instructions do not create that capability.

## Spend API requests on state changes and decisive observations

GitHub recommends webhooks over polling, serial requests, conditional reads
where appropriate, pauses between mutations, and respecting `Retry-After` and
rate-limit reset headers. See [REST API best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).

Decision: use the existing control-plane events and local logs first; one owner
observes a run with bounded backoff. Keep one active GitHub request process,
batch necessary reads, and avoid CI/review polling during an authorized native
development loop. On rate limit, wait at least three minutes and any longer
server-specified deadline. Do not reauthenticate to continue traffic. Preserve
uncertain writes and read them back before another attempt.

## Keep the existing architecture while fixing its feedback loop

GitHub documents ARC for Kubernetes and a Scale Set Client for custom
infrastructure. Their existence is not evidence that replacing the current
control plane is necessary to finish a native canary. Our immediate issue is
incomplete mechanical coverage and serial cross-host handoffs; an orchestrator
migration would add scope before testing the requested behavior. See the
[autoscaling reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners#autoscaling).
