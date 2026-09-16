# Disposable native qualification session

This recipe adapts the existing canonical macOS session owner for an image acceptance fixture. It creates a real nonadministrator GUI session in a **disposable clone** and runs pinned Flutter, Maestro and other tools as that user. It does not register an Actions runner, request JIT, receive agent authentication, modify the host, or qualify a customer's staging app. The reusable images must remain accountless and credential-free.

The lifecycle remains owned by `uxmaltech-collab/ai-templates-resources/runners/control-plane`. `module-lock.json` records its immutable release pin and the exact six module hashes already accepted through the consumer. No owner module is forked or committed here. The empty package marker follows the native installer's isolated-package layout; the repository's regular initializer would import the unrelated routing stack.

## Resolve the canonical dependency

Use an existing checkout containing the locked owner commit. This command reads local Git objects and performs no network, guest or host-service operation:

```sh
python3 recipes/qualification-session/prepare-payload.py \
  --source-checkout /absolute/canonical/templates-checkout \
  --source-kind templates \
  --output /absolute/private/new-qualification-payload
```

The accepted consumer checkout can also supply the same exact bytes with `--source-kind consumer`. Every module is verified against its locked length and SHA-256 before any output is created. Supply `--git /absolute/git` when the host's default Git requires unavailable developer tools. Existing output is never overwritten.

The generated `MODULES.json` retains both the accepted source identity and the checkout used to resolve its bytes. `PAYLOAD-MANIFEST.json` declares all staged file hashes and modes. Keep generated dependencies outside this repository and outside any sealed reusable image.

## Install only in a qualification clone

After finalizing the reusable Flutter image, create a new owned acceptance clone using the host's image operation. Stage the verified payload through its existing root RPC into a new `/opt/ai-runner-qualification`. Directories are root-owned0755, helper0755, modules and metadata0644. Verify all bytes after staging. The helper uses `/opt/macos-tart-bootstrap/python/bin/python3.12 -I`; it needs no pip packages or system Python.

Create `/opt/ai-runner-qualification/commands` root-owned0755 and `/private/var/lib/ai-runner-qualification` root-owned0700. Then stage root-owned0644 `qualification.json` with these inputs:

| Field | Required value |
| --- | --- |
| `schema_version` | `1` |
| `qualification_only` | `true` |
| `image_export_permitted` | `false` |
| `repository` | `uxmaltech-collab/ai-runner-images` |
| `recipe_commit` | Actual committed qualification recipe, 40 hexadecimal characters |
| `session_source_commit` | `3a3e163793d85a2110a7de5098ffe2a2f90b2f3b`, the accepted dependency identity |
| `image` | Actual finalized parent layer's immutable image identity |
| `deadline_unix` | Future numeric deadline for this entire qualification attempt |
| `resources` | Actual assigned `cpus`, `memory_mib`, `disk_gb` |
| `guest_user`, `guest_home` | The declared disposable runner identity |
| `session_policy` | Schema2 with distinct `provisioner` and `runner` objects containing `name`, `uid`, `gid:20`, and `/Users/<name>` home |
| `environment` | Explicit tool PATH, DEVELOPER_DIR, JAVA_HOME and any public SDK settings |
| `tools` | Map of tool names to absolute `path`, SHA-256 of the resolved executable, `version_args` array and nonempty `version_contains` |

For example, fixture roles can be `qualifier-setup`UID501 and `qualifier`UID502 with GID20 and matching homes. These are **guest fixture assignments**, not host account bindings. The owner verifies there are no existing ordinary guest accounts or autologin state and rejects occupied IDs/homes. Do not change accounts manually after a failed transaction.

Include the tools needed by acceptance, such as Flutter, Dart, Maestro and `/usr/bin/xcrun`, plus any agent version checks. The qualification callback supports this map without extending the production guest's closed tools schema. Measure real executable bytes and bind the actual expected versions. Version commands must not require authentication. Authentication/session values must never appear in this configuration or environment.

## Prepare, reboot and prove readiness

The following commands execute **inside the disposable guest** through the existing bounded root RPC owner:

```text
/opt/ai-runner-qualification/qualification-session.py prepare
/opt/ai-runner-qualification/qualification-session.py shutdown
```

Run `prepare` once and require `session-prepared`, `session_phase=prepared`, `reboot_required=true`. The wrapper generates fresh credentials inside the guest; the canonical owner performs account creation, password verification, provisioner disablement and temporary runtime autologin. Password buffers are wiped and no credential value or derived hash enters its public receipts.

Let normal shutdown finish and retain the host's process/holder cleanup receipt. If RPC disconnects during poweroff, reconcile the durable shutdown intent and stopped VM; do not repeat the transaction. Boot the same acceptance clone again and invoke:

```text
/opt/ai-runner-qualification/qualification-session.py status
```

Require `ready`, a different boot, the actual configured console/Aqua identity, nonadministrator runner, disabled provisioner and secure token false. The owner records actual tool executable hashes and version output in `session-v2/tools-<boot-sha>.json`. Observe transient GUI initialization with bounded status calls; never retry account preparation. A failed or interrupted version probe is not converted into a pass.

The canonical owner accepts `JobRequest`, not a separate session-only request type. Here it is used solely as a local qualification identity envelope. `LOCAL-IDENTITY.json` explicitly records `github_job_created=false`, `jit_created=false` and `image_export_permitted=false`. Its local numeric identifiers are not GitHub jobs, workflow runs or production leases.

## Build and test in the nonadministrator GUI context

Create root-controlled command JSON files under `/opt/ai-runner-qualification/commands`. Each declares a tool already pinned in `qualification.json`, string arguments and an existing working directory beneath the runner's real home. Example `hello-create.json`:

```json
{"tool":"flutter","args":["create","--platforms=ios","--org","com.uxmaltech.qualification","hello_world"],"cwd":"/Users/qualifier"}
```

Run it through the host's bounded process/log owner:

```text
/bin/launchctl asuser 502 /opt/ai-runner-qualification/qualification-session.py gui-exec /opt/ai-runner-qualification/commands/hello-create.json
```

Substitute the actual runner UID. The helper verifies Aqua and the nonadministrator account, then applies the production owner's `setgroups([])`, `setgid`, `setuid` sequence and checks real POSIX groups before executing the pinned tool. `launchctl asuser` alone does not drop privileges.

Prepare equivalent commands for the real Flutter simulator build, `xcrun simctl` create/boot/install/launch and Maestro execution. Bind the actual simulator UDID, app path and assertion flow. Collect build logs, app metadata, screenshots, JUnit, exit status and cleanup. A ready session or tool version proves neither an app build nor a passing UI test.

Ensure the SDK cache strategy supports nonadministrator execution. This helper does not silently change permissions on a sealed Flutter tree. Use the image recipe's declared writable cache arrangement or a per-user SDK copy and record that choice.

## Recovery and evidence

Preserve failed session state and partial evidence. After any interrupted account transaction, inspect the recorded state; do not reuse its one-time password preparation. Collect only safe session receipts, build/test output and explicit cleanup evidence through the root RPC. Never export `/private/etc/kcpassword`, password metadata contents, or the credential-bearing qualification disk.

Stop and dispose of the owned qualification clone through the host owner, preserving the sealed layers and original builders. Record the real clone/process/simulator cleanup result. Recipe preparation provides syntax/import/lock verification only; actual native preparation, GUI readiness, Flutter build and Maestro results require their own execution receipts.
