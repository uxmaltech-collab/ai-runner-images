# syntax=docker/dockerfile:1.7
# runner-agent-base — runner-base plus the three agent harnesses (Claude Code,
# Codex CLI, Grok CLI), Python 3.12 and the browser runtime: the technology
# stack, which changes rarely. It carries no Collab runtime: each leaf image
# installs Collab as its last layer, so a Collab release rebuilds only that
# layer and every stack layer stays cached. One image serves every resolver profile; the
# control plane's catalog decides which harness a profile invokes and which
# auth seed it receives, so the image itself excludes nothing.
ARG RUNNER_BASE_IMAGE
ARG PYTHON_BASE_IMAGE=docker.io/library/python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
FROM ${PYTHON_BASE_IMAGE} AS collab-python
FROM ${RUNNER_BASE_IMAGE} AS agents

# The exact harness pins have no default here: the consumer passes the
# Templates canon class's compatibility/harness-pins.yaml (collab.harness-pins/v1)
# as build arguments, and a build without them stops. Grok is the vendor's
# versioned Linux binary, verified against its per-architecture digest.
ARG CLAUDE_CODE_VERSION
ARG CODEX_CLI_VERSION
ARG GROK_CLI_VERSION
ARG GROK_SHA256_AMD64
ARG GROK_SHA256_ARM64
ARG TARGETARCH
LABEL org.opencontainers.image.title="runner-agent-base" \
      io.uxmaltech.runner.engines="claude,codex,grok" \
      io.uxmaltech.runner.lineage="runner-base,runner-agent-base" \
      io.uxmaltech.runner.engine.claude.version="${CLAUDE_CODE_VERSION}" \
      io.uxmaltech.runner.engine.codex.version="${CODEX_CLI_VERSION}" \
      io.uxmaltech.runner.engine.grok.version="${GROK_CLI_VERSION}"

# A digest-pinned image must never self-update its harness binaries at job time.
ENV DISABLE_AUTOUPDATER=1

USER root
RUN for pin in "${CLAUDE_CODE_VERSION}" "${CODEX_CLI_VERSION}" "${GROK_CLI_VERSION}" "${GROK_SHA256_AMD64}" "${GROK_SHA256_ARM64}"; do \
      test -n "${pin}" || { echo "the harness pins are build arguments of compatibility/harness-pins.yaml" >&2; exit 1; }; \
    done; \
    command -v npm >/dev/null || \
    { echo "runner-base must provide npm" >&2; exit 1; }; \
    node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' || \
    { echo "runner-base must provide Node.js 20 or newer for the npm harnesses" >&2; exit 1; }
RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
      amd64) grok_platform=linux-x86_64; grok_sha="${GROK_SHA256_AMD64}" ;; \
      arm64) grok_platform=linux-aarch64; grok_sha="${GROK_SHA256_ARM64}" ;; \
      *) echo "unsupported harness architecture" >&2; exit 1 ;; \
    esac; \
    npm install --global "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" "@openai/codex@${CODEX_CLI_VERSION}"; \
    npm cache clean --force; \
    curl -fsSL "https://x.ai/cli/grok-${GROK_CLI_VERSION}-${grok_platform}" -o /tmp/grok \
      || curl -fsSL "https://storage.googleapis.com/grok-build-public-artifacts/cli/grok-${GROK_CLI_VERSION}-${grok_platform}" -o /tmp/grok; \
    echo "${grok_sha}  /tmp/grok" | sha256sum -c -; \
    install -m 0755 /tmp/grok /usr/local/bin/grok; \
    rm -f /tmp/grok; \
    claude --version; \
    codex --version; \
    grok --version | grep -F "${GROK_CLI_VERSION}"

# Python 3.12 for the Collab runtime each leaf image installs last.
COPY --from=collab-python /usr/local/ /usr/local/
ARG PYTHON_BASE_IMAGE
RUN case "${PYTHON_BASE_IMAGE}" in *@sha256:*) ;; *) exit 1 ;; esac && ldconfig && python3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)"

# One browser runtime is inherited by every flavor. Its pinned Playwright
# release selects Chromium; the same executable supports direct Archify checks.
ARG PLAYWRIGHT_VERSION=1.63.0
ARG PLAYWRIGHT_CHROMIUM_VERSION=153.0.8010.12
ARG PLAYWRIGHT_CHROMIUM_REVISION=1243
ENV PLAYWRIGHT_VERSION=${PLAYWRIGHT_VERSION} \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright/browsers \
    ARCHIFY_CHROME=/usr/local/bin/archify-chrome \
    ARCHIFY_CHROME_NO_SANDBOX=1
LABEL io.uxmaltech.playwright.version="${PLAYWRIGHT_VERSION}" \
      io.uxmaltech.playwright.chromium.version="${PLAYWRIGHT_CHROMIUM_VERSION}" \
      io.uxmaltech.playwright.chromium.revision="${PLAYWRIGHT_CHROMIUM_REVISION}"
RUN set -eux; \
    npm install --global "@playwright/test@${PLAYWRIGHT_VERSION}"; \
    npm cache clean --force; \
    playwright --version | grep -qx "Version ${PLAYWRIGHT_VERSION}"; \
    install -d -m 0755 "${PLAYWRIGHT_BROWSERS_PATH}"; \
    playwright install --with-deps chromium; \
    chromium="$(node -e 'process.stdout.write(require(process.argv[1]).chromium.executablePath())' "$(npm root -g)/@playwright/test")"; \
    case "${chromium}" in "${PLAYWRIGHT_BROWSERS_PATH}/chromium-${PLAYWRIGHT_CHROMIUM_REVISION}/"*) ;; \
      *) echo "Chromium revision differs from its pin" >&2; exit 1 ;; esac; \
    shell="$(find "${PLAYWRIGHT_BROWSERS_PATH}/chromium_headless_shell-${PLAYWRIGHT_CHROMIUM_REVISION}" -type f -name chrome-headless-shell)"; \
    test -x "${chromium}"; test -x "${shell}"; \
    for binary in "${chromium}" "${shell}"; do \
      if ldd "${binary}" | grep -q "not found"; then echo "unresolved Chromium shared libraries" >&2; exit 1; fi; \
    done; \
    reported="$("${chromium}" --headless --no-sandbox --version | tr -d '\n')"; \
    case "${reported}" in *"${PLAYWRIGHT_CHROMIUM_VERSION}"*) ;; \
      *) echo "Chromium version differs from its pin" >&2; exit 1 ;; esac; \
    playwright screenshot --browser chromium "data:text/html,<title>headless shell</title>" /tmp/launch-shell.png; \
    playwright screenshot --browser chromium --channel chromium "data:text/html,<title>chromium</title>" /tmp/launch-chromium.png; \
    test -s /tmp/launch-shell.png; test -s /tmp/launch-chromium.png; \
    rm -f /tmp/launch-shell.png /tmp/launch-chromium.png; \
    rm -rf /var/lib/apt/lists/*; \
    chmod -R a+rX,go-w /opt/playwright; \
    printf '{\n  "playwright": "%s",\n  "package": "@playwright/test",\n  "chromium": "%s",\n  "chromium_revision": "%s",\n  "chromium_headless_shell_revision": "%s",\n  "browsers_path": "%s",\n  "os": "%s"\n}\n' \
      "${PLAYWRIGHT_VERSION}" "${PLAYWRIGHT_CHROMIUM_VERSION}" \
      "${PLAYWRIGHT_CHROMIUM_REVISION}" "${PLAYWRIGHT_CHROMIUM_REVISION}" \
      "${PLAYWRIGHT_BROWSERS_PATH}" "$(. /etc/os-release && echo "${PRETTY_NAME}")" \
      > /opt/playwright/versions.json; \
    chmod 0644 /opt/playwright/versions.json; \
    printf '%s\n' '#!/bin/sh' "exec ${chromium} --disable-dev-shm-usage \"\$@\"" > "${ARCHIFY_CHROME}"; \
    chmod 0755 "${ARCHIFY_CHROME}"

USER runner

# The final image carries the stack only; no Collab runtime and no organization code.
FROM agents AS consumer
RUN python3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" && claude --version && codex --version && grok --version

# The pack revision changes with every publication. Declared last, it labels the
# image without invalidating any cached layer above it.
ARG RUNNER_BASE_REVISION
LABEL org.opencontainers.image.revision="${RUNNER_BASE_REVISION}"
