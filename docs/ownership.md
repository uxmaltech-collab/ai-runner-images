# Source and operational ownership

| Surface | Existing owner |
| --- | --- |
| Current Collab host SRE installer, native executor, guest/session/RPC and control-plane implementations | `uxmaltech-collab/cli`, installed through its published runtime/providers; Templates owns shared declarative instructions. Historical qualification modules retain their explicitly recorded Templates pins. |
| All runner image recipes and toolchain installation/launch support for iOS/macOS, Android, Linux, web and future platforms; compatibility locks, artifact catalog and qualification fixtures/history | `uxmaltech-collab/ai-runner-images` |
| Ordinary CLI/hydration, consumer journey driver and command registration | Their existing CLI/library/resource-pack owner; upstream extraction is explicit work |
| Agent catalog, GitHub/OIDC/account references, repository environment and publication policy | Each organization's resource-pack/control-plane deployment |
| Build adapter, app environment semantics, application/package code, smoke and journey flows | The relevant application/package repositories |
| Account IDs, APFS allocation, SSH endpoint, keychain/service context and capacity | Installed host declaration and its operator |
| Evidence publication and immutable byte verification | Existing external publisher with organization-scoped authority |

This repository is the common home for images and runner tools across organizations. It owns how toolchains are obtained, installed, composed and qualified. Existing upstream tools and runtime components retain their implementation owners; recipes consume exact compatible releases. Correct shared defects in their owner and consume the merged release. This scope does not create another executor, agent persona, credential broker or publisher, or silently transfer a consumer-specific driver to this repository.

The accepted native reference belongs to `enviaflores/ef-storefront-ios`. [Flutter iOS Hello World passed its separate neutral qualification](../qualification/flutter-ios-hello-world-20260916/README.md). The Linux CI stack has a separate build and cold-restore qualification in `stacks/linux-control-plane`; its [real GitHub E2E and cleanup passed](../qualification/linux-control-plane-20260917/GITHUB-E2E.json) in the designated collab-e2e-org tenant. Android and web retain their own qualification boundaries. Lastmile integration belongs to `enviaflores/ef-lastmile-flutter` plus `enviaflores/lastmile-drivers-pkg-flutter`, with their resolved shared dependency closure. None proves multi-organization isolation by itself.

Named maintainers and CODEOWNERS are intentionally not invented here. Existing user authorization remains valid for its scope; an ownership handoff or operation substep does not by itself require another confirmation.

Historical findings include a real SSH service-ACL repair outside the then-current reusable installer and application/command hardcoding in the consumer. Do not assume those gaps are fixed merely because the first Mac works. Track their canonical owner changes and resulting receipts; see [lessons](research/2026-09-16/LESSONS-AND-FAILURES.md) and [baseline audit](research/2026-09-16/OWNERSHIP-AND-BASELINE.md).
