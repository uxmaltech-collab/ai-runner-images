# syntax=docker/dockerfile:1.7
# agent-base — the harness-complete base image of every agent session container.
#
# One image carries the three harnesses (Claude Code, Codex CLI, Grok CLI) plus
# the toolchain every agent session needs (git, gh, Node.js 22, Python 3.12, ripgrep).
# Which harness a session uses is decided at session time by the host's account
# declaration, never by the image. Flavors extend this image per repository
# type (see flavors/EXAMPLE.Dockerfile) and inherit the installed Collab runtime and
# the repository's stack; nothing organization-specific lives here.
#
# Every download is version-pinned by build argument and digest-verified; the
# base OS image is digest-qualified. Override the ARG defaults to bump.
ARG PYTHON_BASE_IMAGE=docker.io/library/python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
ARG AGENT_BASE_OS_IMAGE=node:22-trixie@sha256:2082d2bf902c8835655c6bcfee3594c00ea900498a9f6e2b96d3352536f9e8d8
FROM ${PYTHON_BASE_IMAGE} AS collab-python-runtime

FROM ${AGENT_BASE_OS_IMAGE}
COPY --from=collab-python-runtime /usr/local/ /usr/local/
RUN ldconfig && python3.12 --version

ARG AGENT_BASE_OS_IMAGE
ARG AGENT_BASE_REVISION=unknown
ARG CLAUDE_CODE_VERSION=2.1.296
ARG CODEX_CLI_VERSION=0.162.1
ARG GROK_CLI_VERSION=1.0.50
ARG GROK_INSTALLER_SHA256=7fd6fdc75d9418b2e58356726fcbf1ae849416f773925da07d0ccc7a60d3e791
ARG GH_VERSION=2.96.0
ARG GH_SHA256_AMD64=83d5c2ccad5498f58bf6368acb1ab32588cf43ab3a4b1c301bf36328b1c8bd60
ARG GH_SHA256_ARM64=06f86ec7103d41993b76cd78072f43595c34aaa56506d971d9860e67140bf909
ARG AGENT_UID=1000
ARG AGENT_GID=1000
ARG TARGETARCH

LABEL org.opencontainers.image.title="agent-base" \
      org.opencontainers.image.description="Harness-complete base image of agent session containers: Claude Code, Codex CLI and Grok CLI on one toolchain." \
      org.opencontainers.image.revision="${AGENT_BASE_REVISION}" \
      io.uxmaltech.agent.harnesses="claude,codex,grok" \
      io.uxmaltech.agent.harness.claude.version="${CLAUDE_CODE_VERSION}" \
      io.uxmaltech.agent.harness.codex.version="${CODEX_CLI_VERSION}" \
      io.uxmaltech.agent.harness.grok.version="${GROK_CLI_VERSION}" \
      io.uxmaltech.agent.lineage="agent-base"

ENV DEBIAN_FRONTEND=noninteractive \
    AGENT_HOME=/home/agent \
    PATH="/home/agent/.local/bin:${PATH}"

# Toolchain and the session account. The OS image's default account (uid 1000)
# is replaced by `agent` so the uid stays predictable for bind mounts.
RUN case "${AGENT_BASE_OS_IMAGE}" in *@sha256:*) ;; \
      *) echo "AGENT_BASE_OS_IMAGE must be digest-qualified" >&2; exit 1 ;; esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential ca-certificates curl fd-find git gnupg jq less openssh-client \
      procps python3 python3-pip python3-venv ripgrep tar unzip xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && if id node >/dev/null 2>&1; then userdel -r node; fi \
    && groupadd --gid "${AGENT_GID}" agent \
    && useradd --uid "${AGENT_UID}" --gid "${AGENT_GID}" --create-home --shell /bin/bash agent \
    && install -d -o agent -g agent -m 0755 /work /home/agent/.local/bin

# GitHub CLI, digest-verified per architecture.
RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
      amd64) tool_arch=amd64; gh_sha="${GH_SHA256_AMD64}" ;; \
      arm64) tool_arch=arm64; gh_sha="${GH_SHA256_ARM64}" ;; \
      *) echo "unsupported tool architecture" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${tool_arch}.tar.gz" -o /tmp/gh.tar.gz; \
    echo "${gh_sha}  /tmp/gh.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/gh.tar.gz -C /tmp; \
    install -m 0755 "/tmp/gh_${GH_VERSION}_linux_${tool_arch}/bin/gh" /usr/local/bin/gh; \
    rm -rf /tmp/gh.tar.gz "/tmp/gh_${GH_VERSION}_linux_${tool_arch}"; \
    gh --version

# The three harnesses. Claude Code and Codex come from npm at exact versions;
# Grok from x.ai's installer, itself digest-verified, at an exact version, with
# the binary placed on the system path (not under a user home).
RUN set -eux; \
    npm install --global "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" "@openai/codex@${CODEX_CLI_VERSION}"; \
    npm cache clean --force; \
    curl -fsSL https://x.ai/cli/install.sh -o /tmp/install-grok.sh; \
    echo "${GROK_INSTALLER_SHA256}  /tmp/install-grok.sh" | sha256sum -c -; \
    install -d -m 0755 /opt/grok; \
    HOME=/opt/grok GROK_BIN_DIR=/usr/local/bin bash /tmp/install-grok.sh "${GROK_CLI_VERSION}"; \
    rm -f /tmp/install-grok.sh; \
    chmod -R a+rX /opt/grok; \
    claude --version; \
    codex --version; \
    grok --version

# Install the exact verified Collab runtime and locked dependencies offline.
COPY collab-release/ /tmp/collab-release/
RUN python3.12 /tmp/collab-release/install.py install --artifacts /tmp/collab-release --prefix /opt/collab/runtime \
    && rm -rf /tmp/collab-release \
    && chmod -R a+rX,go-w /opt/collab
ENV PATH=/opt/collab/runtime/bin:$PATH

# One browser runtime is inherited by every flavor. Its pinned Playwright
# release selects Chromium; the same executable supports direct Archify checks.
ARG PLAYWRIGHT_VERSION=1.63.0
ARG PLAYWRIGHT_CHROMIUM_VERSION=153.0.8010.12
ARG PLAYWRIGHT_CHROMIUM_REVISION=1243
ENV PLAYWRIGHT_VERSION=${PLAYWRIGHT_VERSION} \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright/browsers \
    COLLAB_BROWSER=/usr/local/bin/collab-chromium \
    COLLAB_BROWSER_NO_SANDBOX=1
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
    printf '%s\n' '#!/bin/sh' "exec ${chromium} --disable-dev-shm-usage \"\$@\"" > "${COLLAB_BROWSER}"; \
    chmod 0755 "${COLLAB_BROWSER}"

WORKDIR /work
USER agent
