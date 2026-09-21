#!/usr/bin/env bash
# ef-storefront-web-stack-install [--offline] [--project <dir>]
#
# Install the storefront-web checkout's own pnpm-lock.yaml inside the
# runner-resolver-storefront-web image, then prove that project Playwright and
# the Playwright MCP are available. The install sequence is the contract of
# enviaflores/ai-repo-resources#27 and honors `packageManager` in package.json:
#
#   corepack enable
#   corepack prepare --activate
#   pnpm install --frozen-lockfile
#
# It never runs `npm ci` and never reads package-lock.json.
#
# The @uxmaltech scope is pinned to GitHub Packages through a temporary npm user
# config that lives outside the checkout and is removed on exit. Its token comes
# only from AI_REPO_RESOURCES_STOREFRONT_WEB_NPM_TOKEN at job time; no value is
# written into the image, the workspace, or the logs. When the lockfile resolves
# packages from that registry and the token is empty, the install fails closed
# before touching the network.
set -euo pipefail

readonly tool="ef-storefront-web-stack-install"
readonly registry_scope="@uxmaltech"
readonly registry_host="npm.pkg.github.com"
readonly token_env="AI_REPO_RESOURCES_STOREFRONT_WEB_NPM_TOKEN"

usage() {
  cat >&2 <<'USAGE'
Usage: ef-storefront-web-stack-install [--offline] [--project <dir>]

Installs the pnpm project in the current directory (or --project) with
`corepack enable`, `corepack prepare --activate`, and
`pnpm install --frozen-lockfile`, then probes project Playwright and the
Playwright MCP. --offline forwards pnpm's --offline flag and forbids Corepack
network access.
USAGE
}

fail() {
  echo "${tool}: $*" >&2
  exit 1
}

offline=0
project="${PWD}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --offline) offline=1 ;;
    --project)
      shift
      [[ $# -gt 0 ]] || { usage; exit 2; }
      project="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
  shift
done

cd "${project}"
[[ -f package.json ]] || fail "package.json not found in ${PWD}"
[[ -f pnpm-lock.yaml ]] || fail "pnpm-lock.yaml not found in ${PWD}; this stack installs only from pnpm-lock.yaml"
[[ ! -e package-lock.json ]] || fail "package-lock.json is present in ${PWD}; the storefront-web stack is pnpm-only and never installs from an npm lockfile"

# Registry configuration: scope pin always, credential only from the secret env.
token="${!token_env:-}"
config_dir="$(mktemp -d "${TMPDIR:-/tmp}/${tool}.XXXXXX")"
cleanup() {
  rm -rf -- "${config_dir}"
}
trap cleanup EXIT
npmrc="${config_dir}/npmrc"
# The directory is 0700 from mktemp; create the file itself as 0600 from the
# start (subshell so the restrictive umask never reaches pnpm's own files).
(umask 077 && : > "${npmrc}")
printf '%s:registry=https://%s\n' "${registry_scope}" "${registry_host}" >> "${npmrc}"
if [[ -n "${token}" ]]; then
  printf '//%s/:_authToken=%s\n' "${registry_host}" "${token}" >> "${npmrc}"
elif grep -qF "${registry_host}" pnpm-lock.yaml; then
  fail "pnpm-lock.yaml resolves packages from ${registry_host} but ${token_env} is empty"
fi
export NPM_CONFIG_USERCONFIG="${npmrc}"

if [[ "${offline}" -eq 1 ]]; then
  export COREPACK_ENABLE_NETWORK=0
fi
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
export COREPACK_ENABLE_AUTO_PIN=0

# Corepack shims: the image enables them in /usr/local/bin at build time; an
# unprivileged job re-enables them in its own PATH-visible directory.
shim_dir=/usr/local/bin
if [[ ! -w "${shim_dir}" ]]; then
  shim_dir="${HOME}/.local/bin"
  mkdir -p "${shim_dir}"
fi
corepack enable --install-directory "${shim_dir}"
corepack prepare --activate
install_args=(install --frozen-lockfile)
if [[ "${offline}" -eq 1 ]]; then
  install_args+=(--offline)
fi
pnpm "${install_args[@]}"

# Project Playwright and MCP availability probes.
node -e "require.resolve('@playwright/test')"
pnpm exec playwright --version
playwright-mcp --version
command -v ef-storefront-web-playwright-mcp >/dev/null
command -v ef-storefront-web-screenshot >/dev/null
echo "${tool}: ok (node $(node --version), pnpm $(pnpm --version), corepack $(corepack --version))"
