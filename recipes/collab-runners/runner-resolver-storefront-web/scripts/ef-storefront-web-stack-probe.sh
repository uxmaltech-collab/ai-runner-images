#!/usr/bin/env bash
# ef-storefront-web-stack-probe
#
# Re-run the storefront-web stack install contract offline against the probe
# project bundled in the image. The publisher's in-image probe calls this after
# every build; it proves the image alone can satisfy a pnpm-lock.yaml with
# --frozen-lockfile and expose project Playwright plus the Playwright MCP.
set -euo pipefail
exec ef-storefront-web-stack-install --offline \
  --project "${EF_STOREFRONT_WEB_STACK_PROBE:-/opt/ef-storefront-web-stack-probe}"
