#!/bin/sh
set -eu

jit_env="${JIT_CONFIG_ENV:-RUNNERS_PACK_JIT_CONFIG}"
case "$jit_env" in
  ''|[0-9]*|*[!A-Z0-9_]*)
    echo "JIT_CONFIG_ENV must name an uppercase environment variable" >&2
    exit 64
    ;;
esac
jit_config="$(printenv "$jit_env" || true)"
if [ -z "$jit_config" ]; then
  echo "$jit_env is required" >&2
  exit 64
fi
exec /actions-runner/run.sh --jitconfig "$jit_config"
