#!/usr/bin/env bash
# ef-storefront-web-screenshot <url> [output.png]
#
# Full-page desktop capture for visual evidence. Resolves Playwright from the
# checkout's node_modules first (installed by ef-storefront-web-stack-install)
# and falls back to the image's global Playwright.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: ef-storefront-web-screenshot <url> [output.png]" >&2
  exit 2
fi
url="$1"
output="${2:-playwright-screenshot.png}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/ms-playwright}"
global_modules="$(npm root -g)"
export NODE_PATH="${NODE_PATH:+${NODE_PATH}:}${global_modules}"
node - "${url}" "${output}" <<'NODE'
const { chromium } = require("playwright");
const [url, output] = process.argv.slice(2);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
  await page.screenshot({ path: output, fullPage: true });
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
NODE
