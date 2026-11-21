#!/usr/bin/env bash
# runner-web-stack-install [--offline] [--project <dir>]
#
# Install the web application checkout's own pnpm-lock.yaml inside the
# runner-resolver-nuxt-pnpm image, then prove that project Playwright and
# the Playwright MCP are available. The install sequence is the pack's pnpm
# contract and honors `packageManager` in package.json:
#
#   corepack enable
#   corepack prepare --activate
#   pnpm install --frozen-lockfile
#
# It never runs `npm ci` and never reads package-lock.json.
#
# Registry configuration is organization data. Each private package scope the install
# needs is declared as `<scope>=<registry-host>[=<credential-variable-name>]` entries,
# separated by spaces, in RUNNER_WEB_REGISTRIES and/or in the image-owned file
# /etc/runner-web-stack/registries (written at build time from the planner's input). The
# helper names the variable that holds a credential, never its value: the value is read
# from the job's environment at install time and goes only into a temporary npm user
# config outside the checkout (mode 0600, removed on exit); it is written into no image,
# workspace or log. The temporary config starts from the user config npm would have used
# ($NPM_CONFIG_USERCONFIG, else ~/.npmrc), so unrelated settings are kept. Nothing here
# stops the install: an entry that cannot be used, an empty credential variable or no
# declaration at all is a warning and the install goes on with what is configured.
set -euo pipefail

readonly tool="runner-web-stack-install"
readonly registries_file="${RUNNER_WEB_STACK_REGISTRIES_FILE:-/etc/runner-web-stack/registries}"

warn() {
  echo "${tool}: WARNING: $*" >&2
}

usage() {
  cat >&2 <<'USAGE'
Usage: runner-web-stack-install [--offline] [--project <dir>]

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
[[ ! -e package-lock.json ]] || fail "package-lock.json is present in ${PWD}; the web stack is pnpm-only and never installs from an npm lockfile"

# Registry configuration, from the declared bindings only.
declared="${RUNNER_WEB_REGISTRIES:-}"
if [[ -r "${registries_file}" ]]; then
  declared="${declared} $(tr '\n' ' ' < "${registries_file}")"
fi
config_dir="$(mktemp -d "${TMPDIR:-/tmp}/${tool}.XXXXXX")"
cleanup() {
  rm -rf -- "${config_dir}"
}
trap cleanup EXIT
npmrc="${config_dir}/npmrc"
# The directory is 0700 from mktemp; create the file itself as 0600 from the
# start (subshell so the restrictive umask never reaches pnpm's own files).
(umask 077 && : > "${npmrc}")
bound=0
set -f  # an entry is data, never a pattern to expand
for entry in ${declared}; do
  IFS== read -r scope host variable extra <<< "${entry}"
  if [[ -n "${extra}" ]] \
    || [[ ! "${scope}" =~ ^@[a-z0-9][a-z0-9._-]*$ ]] \
    || [[ ! "${host}" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?$ ]] \
    || { [[ -n "${variable}" ]] && [[ ! "${variable}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; }; then
    warn "ignored a registry entry that is not <scope>=<host>[=<credential-variable-name>]"
    continue
  fi
  host="${host%/}"
  if [[ "${bound}" -eq 0 ]]; then
    # Keep the settings npm would have read; the entries below are appended after them.
    base_config="${NPM_CONFIG_USERCONFIG:-${HOME:-}/.npmrc}"
    if [[ -f "${base_config}" && -r "${base_config}" ]]; then
      cat -- "${base_config}" >> "${npmrc}"
      printf '\n' >> "${npmrc}"
    fi
  fi
  bound=$((bound + 1))
  printf '%s:registry=https://%s/\n' "${scope}" "${host}" >> "${npmrc}"
  if [[ -n "${variable}" ]]; then
    if [[ -n "${!variable:-}" ]]; then
      printf '//%s/:_authToken=%s\n' "${host}" "${!variable}" >> "${npmrc}"
    else
      warn "the credential variable ${variable} for ${scope} is empty; ${scope} is configured without credentials"
    fi
  fi
done
set +f
if [[ "${bound}" -eq 0 ]]; then
  warn "no registry binding is declared (RUNNER_WEB_REGISTRIES or ${registries_file}); the install uses the npm configuration the job already has, and a lockfile that resolves from a private registry needs the job to supply it"
else
  export NPM_CONFIG_USERCONFIG="${npmrc}"
fi

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
command -v runner-web-playwright-mcp >/dev/null
command -v runner-web-screenshot >/dev/null
echo "${tool}: ok (node $(node --version), pnpm $(pnpm --version), corepack $(corepack --version))"
