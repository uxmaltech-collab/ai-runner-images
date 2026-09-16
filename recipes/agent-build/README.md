# Native agent build layer

Compose this layer once on the declared Tart macOS/Xcode/Maestro parent. It contains **Codex, Claude Code and Grok Build together**. The Flutter/Dart layer inherits all three. An agent-free parent is supported: supply the retained Codex executable and its companion explicitly rather than relying on a previous installation inside the guest.

`pins.json` records immutable byte identities. Claude 2.1.266 and Grok 1.0.24 follow the effective `publish-pins.yaml` harness versions at consumer commit `3a3e163793d85a2110a7de5098ffe2a2f90b2f3b`. Codex deliberately preserves the accepted native 0.151.0 closure rather than upgrading it to the Linux npm pin. Do not use the lower Dockerfile defaults or resolve a moving release channel while building.

## Inputs and provenance

| Tool | Native input | SHA-256 |
| --- | --- | --- |
| Codex 0.151.0 | 231,563,824-byte executable | `98491713ffb196061003ee148636e743997cc31d76144ba7c53462269896891d` |
| Codex companion | 62,703,072-byte `codex-code-mode-host` | `f5c96dc8cca0f760f525076c1f9f4efad31355c0fe18efb56e76df7e40592376` |
| Claude 2.1.266 | 199,422,144-byte native executable | `553d1b9e9e7068b275c0a783c7e139ff6503096f286e674c8c919379fb0eca62` |
| Grok 1.0.24 | 137,364,416-byte native executable | `4291021c1570a7c8610277a3d65490a5e54b50311e222c6b4614264f02a215b3` |

Claude's native URL and checksum are published in its [official versioned manifest](https://downloads.claude.ai/claude-code-releases/2.1.266/manifest.json); its [installation documentation](https://code.claude.com/docs/en/setup) documents native installation and disabling automatic updates. The complete downloaded bytes match the manifest. Static code-signing metadata identifies Anthropic team `Q6L2SF6YDW`; this is not a claim that the manifest signature was independently verified.

Grok's [official installer](https://x.ai/cli/install.sh) selects `macos-aarch64` and the versioned x.ai URL. The pinned installer matches the consumer's existing hash. The measured gzip and expanded binary hashes are in the lock; a separate vendor checksum document was not found. Static code-signing metadata identifies X.AI team `5Y6N3AJ54S`. The public installer is not executed: it otherwise reads existing authentication, changes shell profiles and can download managed configuration. Install the verified native payload directly. [Grok Build documentation](https://docs.x.ai/build/overview) remains the tool's usage reference.

Codex inputs reuse the previously verified official `rust-v0.151.0` release payloads and receipts. Keep the companion beside the main executable. Name the installed main executable **`codex`**, not `codex-aarch64-apple-darwin`: the accepted installation already corrected executable-name dispatch. Never copy a user's Codex home, authentication JSON, provider session or repository cache.

## Installation in the builder guest

Transfer the recipe and the four verified payloads through the owning image-build operation. The names below are guest staging paths, not host paths or assigned accounts. The host builder plan supplies its actual transfer, user and receipt locations. The native image executor, launch/session/RPC and host installer remain in their existing owners.

As root **inside that builder guest**:

```sh
python3 /tmp/agent-build/install.py \
  --artifacts /tmp/agent-payloads \
  --codex-binary /tmp/agent-payloads/codex \
  --codex-companion /tmp/agent-payloads/codex-code-mode-host \
  --receipt /tmp/agent-installation.json
```

`/tmp/agent-payloads` must contain `claude-2.1.266-darwin-arm64` and `grok-1.0.24-macos-aarch64`. The installer verifies all four inputs before creating anything in `/opt`, installs a new protected tree, verifies the copied bytes and records a receipt. It never downloads, authenticates, changes shell startup files, modifies another installation or executes an agent. An existing destination is preserved for receipt reconciliation. Partial staging directories are left for the owner to inspect and clean explicitly.

Installed paths are `/opt/ai-runner-images/agents/bin/{codex,claude,grok}`. Each wrapper invokes its fixed native binary under the same root-owned tree. Claude's wrapper sets `DISABLE_AUTOUPDATER=1`. Jobs receive this `bin` directory through the declared runtime PATH, independent of personal shell configuration. No broadly named `agent` alias is installed.

## Qualification and sealing

As the declared **nonadministrator guest job user**:

```sh
python3 /tmp/agent-build/verify.py --receipt /tmp/agent-versions.json
```

This checks all three `--version` commands with a fresh temporary HOME, an empty environment apart from fixed runtime settings, and a 30-second limit per tool. The temporary home is removed. It does not start an interactive or authenticated agent session. A successful version check proves executable compatibility, not account access or a completed model task.

Record the actual parent identity, install and version receipts, recipe commit and hashes, and the owning image operation's final disk/config/NVRAM identities. Preserve any failure. Remove only this build's transferred staging payloads and temporary receipt copies after exporting receipts. Credentials remain job-time managed inputs and must not enter the sealed image. Stop/finalize/admit through the image owner's existing operation. The subsequent Flutter/Dart qualification uses the resulting full agent layer.

Recipe preparation can verify local payloads without any host installation or binary execution:

```sh
python3 recipes/agent-build/install.py \
  --verify-inputs-only \
  --artifacts /absolute/private/downloads \
  --codex-binary /absolute/verified/codex \
  --codex-companion /absolute/verified/codex-code-mode-host \
  --receipt /absolute/private/new-input-verification.json
```

Input verification, source review and static signing metadata are preparation evidence. Physical guest installation, version checks and image sealing are recorded only when their owning operations actually complete.
