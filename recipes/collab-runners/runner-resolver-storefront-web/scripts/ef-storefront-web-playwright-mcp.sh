#!/usr/bin/env bash
# ef-storefront-web-playwright-mcp [playwright-mcp arguments...]
#
# Headless Chromium Playwright MCP for the storefront-web resolver. The profile
# directory defaults to a location outside the checkout so browser state never
# reaches the atomic publish boundary.
set -euo pipefail
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/ms-playwright}"
export PLAYWRIGHT_MCP_USER_DATA_DIR="${PLAYWRIGHT_MCP_USER_DATA_DIR:-${TMPDIR:-/tmp}/ef-storefront-web-playwright-mcp}"
mkdir -p "${PLAYWRIGHT_MCP_USER_DATA_DIR}"
exec playwright-mcp --headless --browser=chromium --no-sandbox \
  --user-data-dir="${PLAYWRIGHT_MCP_USER_DATA_DIR}" "$@"
