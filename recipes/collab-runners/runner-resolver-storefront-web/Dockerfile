# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
ARG AI_REPO_RESOURCES_PLAYWRIGHT_VERSION=1.61.1
ARG AI_REPO_RESOURCES_PLAYWRIGHT_MCP_VERSION=0.0.76
ARG AI_REPO_RESOURCES_COREPACK_VERSION=0.35.0
ARG AI_REPO_RESOURCES_PNPM_VERSION=11.17.0
LABEL org.opencontainers.image.title="runner-resolver-storefront-web" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.profile="resolver-storefront-web" \
      io.enviaflores.runner.engine="codex" \
      io.enviaflores.runner.stack="nuxt-pnpm"

# Stack runtime for enviaflores/ef-storefront-web: pnpm through Corepack, so the
# checkout's `packageManager` pin is honored. The toolchain is baked here; the
# checkout's own pnpm-lock.yaml is installed at job time by
# ef-storefront-web-stack-install (corepack enable, corepack prepare --activate,
# pnpm install --frozen-lockfile) - never `npm ci`, never package-lock.json. No
# stack image is built from the target repository and nothing is read from the
# predecessor pack. COREPACK_HOME is shared and world-writable so the
# unprivileged runner can activate the pinned package manager offline.
# Keep the stack's Playwright pin separate from the agent base's shared
# @playwright/test runtime and binary. Both package trees remain available.
ENV AI_REPO_RESOURCES_WEB_TOOLS_PREFIX=/opt/ef-storefront-web-tools \
    PATH=/opt/ef-storefront-web-tools/bin:${PATH} \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    COREPACK_HOME=/opt/corepack \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    COREPACK_ENABLE_AUTO_PIN=0 \
    EF_STOREFRONT_WEB_STACK_PROBE=/opt/ef-storefront-web-stack-probe

USER root
COPY recipes/collab-runners/runner-resolver-storefront-web/scripts/ef-storefront-web-stack-install.sh /usr/local/bin/ef-storefront-web-stack-install
COPY recipes/collab-runners/runner-resolver-storefront-web/scripts/ef-storefront-web-stack-probe.sh /usr/local/bin/ef-storefront-web-stack-probe
COPY recipes/collab-runners/runner-resolver-storefront-web/scripts/ef-storefront-web-playwright-mcp.sh /usr/local/bin/ef-storefront-web-playwright-mcp
COPY recipes/collab-runners/runner-resolver-storefront-web/scripts/ef-storefront-web-screenshot.sh /usr/local/bin/ef-storefront-web-screenshot
COPY --chown=runner:runner recipes/collab-runners/runner-resolver-storefront-web/stack-probe /opt/ef-storefront-web-stack-probe
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "Agent base must be digest-qualified" >&2; exit 1 ;; esac \
    && chmod 0755 \
      /usr/local/bin/ef-storefront-web-stack-install \
      /usr/local/bin/ef-storefront-web-stack-probe \
      /usr/local/bin/ef-storefront-web-playwright-mcp \
      /usr/local/bin/ef-storefront-web-screenshot \
    && apt-get update \
    && apt-get install -y --no-install-recommends redis-server redis-tools rsync zip \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global \
      "corepack@${AI_REPO_RESOURCES_COREPACK_VERSION}" \
      "@playwright/mcp@${AI_REPO_RESOURCES_PLAYWRIGHT_MCP_VERSION}" \
    && npm install --global --prefix "${AI_REPO_RESOURCES_WEB_TOOLS_PREFIX}" \
      "playwright@${AI_REPO_RESOURCES_PLAYWRIGHT_VERSION}" \
    && corepack enable --install-directory /usr/local/bin \
    && corepack prepare "pnpm@${AI_REPO_RESOURCES_PNPM_VERSION}" --activate \
    && playwright install --with-deps chromium firefox webkit \
    && mcp_playwright="$(node -p "require('node:path').dirname(require.resolve('playwright/package.json', { paths: ['$(npm root -g)/@playwright/mcp'] }))")" \
    && node "${mcp_playwright}/cli.js" install chromium \
    && chmod -R a+rwX "${PLAYWRIGHT_BROWSERS_PATH}" "${COREPACK_HOME}" \
    && npm cache clean --force \
    && codex --version \
    && corepack --version | grep -Fx "${AI_REPO_RESOURCES_COREPACK_VERSION}" \
    && pnpm --version | grep -Fx "${AI_REPO_RESOURCES_PNPM_VERSION}" \
    && playwright --version | grep -Fx "Version ${AI_REPO_RESOURCES_PLAYWRIGHT_VERSION}" \
    && playwright-mcp --version \
    && redis-server --version
USER runner
# Prove the job-time install contract as the unprivileged runner: the bundled
# probe project installs from its pnpm-lock.yaml with --frozen-lockfile and
# exposes project Playwright plus the MCP; the same proof is then repeated
# offline, which is what the publisher's in-image probe re-runs.
RUN HOME=/home/runner ef-storefront-web-stack-install --project "${EF_STOREFRONT_WEB_STACK_PROBE}" \
    && HOME=/home/runner ef-storefront-web-stack-probe
