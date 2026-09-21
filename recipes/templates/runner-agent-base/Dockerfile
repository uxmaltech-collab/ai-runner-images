# syntax=docker/dockerfile:1.7
# runner-agent-base — runner-base plus the three agent harnesses (Claude Code,
# Codex CLI, Grok CLI) and the separately pinned Collab Python runtime. One image serves every resolver profile; the
# control plane's catalog decides which harness a profile invokes and which
# auth seed it receives, so the image itself excludes nothing.
ARG RUNNER_BASE_IMAGE
ARG PYTHON_BASE_IMAGE=docker.io/library/python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
FROM ${PYTHON_BASE_IMAGE} AS collab-python
FROM ${RUNNER_BASE_IMAGE} AS agents

ARG RUNNER_BASE_IMAGE
ARG RUNNER_BASE_REVISION
ARG CLAUDE_CODE_VERSION=2.1.251
ARG CODEX_CLI_VERSION=0.151.0
ARG GROK_CLI_VERSION=1.0.13
# The x.ai installer script has no version pin of its own; the consumer pins
# its checksum (the script changes upstream without notice).
ARG GROK_INSTALLER_SHA256
LABEL org.opencontainers.image.title="runner-agent-base" \
      org.opencontainers.image.revision="${RUNNER_BASE_REVISION}" \
      io.uxmaltech.runner.engines="claude,codex,grok" \
      io.uxmaltech.runner.lineage="runner-base,runner-agent-base" \
      io.uxmaltech.runner.engine.claude.version="${CLAUDE_CODE_VERSION}" \
      io.uxmaltech.runner.engine.codex.version="${CODEX_CLI_VERSION}" \
      io.uxmaltech.runner.engine.grok.version="${GROK_CLI_VERSION}"

# A digest-pinned image must never self-update its harness binaries at job time.
ENV DISABLE_AUTOUPDATER=1

USER root
RUN case "${RUNNER_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "RUNNER_BASE_IMAGE must be digest-qualified" >&2; exit 1 ;; esac || \
    { echo "RUNNER_BASE_IMAGE must be digest-qualified" >&2; exit 1; }; \
    test -n "${RUNNER_BASE_REVISION}" || \
    { echo "RUNNER_BASE_REVISION is required" >&2; exit 1; }; \
    test -n "${GROK_INSTALLER_SHA256}" || \
    { echo "GROK_INSTALLER_SHA256 is required" >&2; exit 1; }; \
    command -v npm >/dev/null || \
    { echo "runner-base must provide npm" >&2; exit 1; }; \
    node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' || \
    { echo "runner-base must provide Node.js 20 or newer for the npm harnesses" >&2; exit 1; }
RUN npm install --global "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" "@openai/codex@${CODEX_CLI_VERSION}" \
    && npm cache clean --force \
    && curl -fsSL https://x.ai/cli/install.sh -o /tmp/install-grok.sh \
    && echo "${GROK_INSTALLER_SHA256}  /tmp/install-grok.sh" | sha256sum -c - \
    && install -d -m 0755 /opt/grok \
    && HOME=/opt/grok GROK_BIN_DIR=/usr/local/bin bash /tmp/install-grok.sh "${GROK_CLI_VERSION}" \
    && rm -f /tmp/install-grok.sh \
    && chmod -R a+rX /opt/grok \
    && claude --version \
    && codex --version \
    && grok --version

# One verified Collab distribution supplies the CLI and Archify Python runtime.
COPY --from=collab-python /usr/local/ /usr/local/
ARG PYTHON_BASE_IMAGE
RUN case "${PYTHON_BASE_IMAGE}" in *@sha256:*) ;; *) exit 1 ;; esac && ldconfig && python3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)"
COPY collab-release /opt/collab-release
RUN python3.12 /opt/collab-release/install.py install --artifacts /opt/collab-release --prefix /opt/collab/runtime
ENV PATH="/opt/collab/runtime/bin:${PATH}" \
    ARCHIFY_PUBLISH_PYTHON=/opt/collab/runtime/bin/python \
    ARCHIFY_UPDATE_CHECK_DISABLED=1

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

# The final image inherits the common installed runtime; no organization code.
FROM agents AS consumer
RUN collab --version
