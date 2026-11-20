#!/usr/bin/env bash
# runner-web-stack-probe
#
# Re-run the web stack install contract offline against the probe
# project bundled in the image. The publisher's in-image probe calls this after
# every build; it proves the image alone can satisfy a pnpm-lock.yaml with
# --frozen-lockfile and expose project Playwright plus the Playwright MCP.
set -euo pipefail
exec runner-web-stack-install --offline \
  --project "${RUNNER_WEB_STACK_PROBE:-/opt/runner-web-stack-probe}"
