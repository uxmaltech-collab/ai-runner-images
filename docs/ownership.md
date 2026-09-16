# Source and operational ownership

| Surface | Existing owner |
| --- | --- |
| Host SRE installer, native executor, guest/session/RPC protocol and shared control-plane contracts | `uxmaltech-collab/ai-templates-resources`, consumed through canonical pins |
| Image recipes, compatibility locks, release catalog and qualification fixtures/history | `uxmaltech-collab/ai-runner-images` |
| Ordinary CLI/hydration, consumer journey driver and command registration | Their existing CLI/library/resource-pack owner; upstream extraction is explicit work |
| Agent catalog, GitHub/OIDC/account references, repository environment and publication policy | Each organization's resource-pack/control-plane deployment |
| Build adapter, app environment semantics, application/package code, smoke and journey flows | The relevant application/package repositories |
| Account IDs, APFS allocation, SSH endpoint, keychain/service context and capacity | Installed host declaration and its operator |
| Evidence publication and immutable byte verification | Existing external publisher with organization-scoped authority |

This repository composes these components; it does not establish a second executor, agent persona, credential broker or publisher. Correct shared defects in their owner and consume the merged release. Do not silently fork consumer-specific code to make a recipe appear generic.

The accepted native reference belongs to `enviaflores/ef-storefront-ios`. Flutter Hello World is a separate proposed qualification. Lastmile integration belongs to `enviaflores/ef-lastmile-flutter` plus `enviaflores/lastmile-drivers-pkg-flutter`, with their resolved shared dependency closure. None proves multi-organization isolation by itself.

Named maintainers and CODEOWNERS are intentionally not invented here. Existing user authorization remains valid for its scope; an ownership handoff or operation substep does not by itself require another confirmation.

Historical findings include a real SSH service-ACL repair outside the then-current reusable installer and application/command hardcoding in the consumer. Do not assume those gaps are fixed merely because the first Mac works. Track their canonical owner changes and resulting receipts; see [lessons](research/2026-09-16/LESSONS-AND-FAILURES.md) and [baseline audit](research/2026-09-16/OWNERSHIP-AND-BASELINE.md).
