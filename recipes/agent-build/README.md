# Native agent build layer

Compose this layer once on the declared Tart macOS/Xcode/Maestro parent. It contains **Codex, Claude Code and Grok Build together**. The Flutter/Dart layer inherits all three. An agent-free parent is supported: supply the retained Codex executable and its companion explicitly rather than relying on a previous installation inside the guest.

The exact releases and their digests are not in this repository. They are the consumer's adopted `collab.harness-pins/v2` document, `compatibility/harness-pins.yaml` of its resource pack, released by the Templates canon class and materialized there verbatim. The native build takes that file as its `harness_pins` input and stages it beside this recipe as `harness-pins.yaml`; the installer reads the versions and the `darwin-arm64` digests of `claude`, `codex`, its `codex-code-mode-host` companion and `grok` from it. A document of another schema, or one that lacks one of those four digests, is refused before anything is installed. Moving a version is a release of the canon class and its adoption by the consumer, never an edit here. Do not resolve a moving release channel while building.

## Inputs and provenance

Each digest is the SHA-256 of the vendor's versioned native executable; byte sizes are not pinned. The offline input names and the vendor sources are derived from the pinned versions by `install.py`:

| Engine | Offline input | Published as |
| --- | --- | --- |
| Codex | `codex` | the executable inside `https://github.com/openai/codex/releases/download/rust-v<version>/codex-aarch64-apple-darwin.tar.gz` |
| Codex companion | `codex-code-mode-host` | the executable inside `codex-code-mode-host-aarch64-apple-darwin.tar.gz` of the same release |
| Claude Code | `claude-<version>-darwin-arm64` | `https://downloads.claude.ai/claude-code-releases/<version>/darwin-arm64/claude` |
| Grok Build | `grok-<version>-macos-aarch64` | `https://x.ai/cli/grok-<version>-macos-aarch64` |

Claude's digest equals the checksum in its official versioned release manifest; its [installation documentation](https://code.claude.com/docs/en/setup) documents native installation and disabling automatic updates. A matching checksum is not a claim that the manifest signature was independently verified.

Grok's public installer is not executed: it otherwise reads existing authentication, changes shell profiles and can download managed configuration. Install the verified native payload directly. [Grok Build documentation](https://docs.x.ai/build/overview) remains the tool's usage reference.

Keep the Codex companion beside the main executable. Name the installed main executable **`codex`**, not `codex-aarch64-apple-darwin`: the accepted installation already corrected executable-name dispatch. Never copy a user's Codex home, authentication JSON, provider session or repository cache.

## Installation in the builder guest

Transfer the recipe, the consumer's adopted harness pins and the four verified payloads through the owning image-build operation. The names below are guest staging paths, not host paths or assigned accounts. The host builder plan supplies its actual transfer, user and receipt locations. The native image executor, launch/session/RPC and host installer remain in their existing owners.

As root **inside that builder guest**:

```sh
python3 /tmp/agent-build/install.py \
  --harness-pins /tmp/agent-build/harness-pins.yaml \
  --artifacts /tmp/agent-payloads \
  --codex-binary /tmp/agent-payloads/codex \
  --codex-companion /tmp/agent-payloads/codex-code-mode-host \
  --receipt /tmp/agent-installation.json
```

`/tmp/agent-build/harness-pins.yaml` is the transferred copy of the consumer's adopted document. `/tmp/agent-payloads` must contain `claude-<version>-darwin-arm64` and `grok-<version>-macos-aarch64` for the pinned versions. The installer verifies all four inputs before creating anything in `/opt`, installs a new protected tree, verifies the copied bytes and records a receipt. It never downloads, authenticates, changes shell startup files, modifies another installation or executes an agent. An existing destination is preserved for receipt reconciliation. Partial staging directories are left for the owner to inspect and clean explicitly.

Installed paths are `/opt/ai-runner-images/agents/bin/{codex,claude,grok}`. The tree keeps `harness-pins.yaml`, the exact document it was installed from, as its receipt: the version check below and a later derivative that inherits this layer read it, and a derivative is refused when the staged document pins other versions or digests. An agent layer sealed before this recipe read the harness pins carries a `pins.json` receipt instead; it is not reused as a parent: compose a new agent layer from the base parent. Each wrapper invokes its fixed native binary under the same root-owned tree. Claude's wrapper sets `DISABLE_AUTOUPDATER=1`. Jobs receive this `bin` directory through the declared runtime PATH, independent of personal shell configuration. No broadly named `agent` alias is installed.

## Qualification and sealing

As the declared **nonadministrator guest job user**:

```sh
python3 /tmp/agent-build/verify.py --receipt /tmp/agent-versions.json
```

This verifies the installed executables against the layer's `harness-pins.yaml` and checks all three `--version` commands with a fresh temporary HOME, an empty environment apart from fixed runtime settings, and a 30-second limit per tool. The temporary home is removed. It does not start an interactive or authenticated agent session. A successful version check proves executable compatibility, not account access or a completed model task.

Record the actual parent identity, install and version receipts, recipe commit and hashes, and the owning image operation's final disk/config/NVRAM identities. Preserve any failure. Remove only this build's transferred staging payloads and temporary receipt copies after exporting receipts. Credentials remain job-time managed inputs and must not enter the sealed image. Stop/finalize/admit through the image owner's existing operation. The subsequent Flutter/Dart qualification uses the resulting full agent layer.

Recipe preparation can verify local payloads without any host installation or binary execution:

```sh
python3 recipes/agent-build/install.py \
  --verify-inputs-only \
  --harness-pins /absolute/consumer-pack/compatibility/harness-pins.yaml \
  --artifacts /absolute/private/downloads \
  --codex-binary /absolute/verified/codex \
  --codex-companion /absolute/verified/codex-code-mode-host \
  --receipt /absolute/private/new-input-verification.json
```

Input verification and source review are preparation evidence. Physical guest installation, version checks and image sealing are recorded only when their owning operations actually complete.
