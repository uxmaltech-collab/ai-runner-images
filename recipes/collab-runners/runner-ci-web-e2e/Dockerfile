# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
ARG AI_REPO_RESOURCES_PLAYWRIGHT_VERSION=1.61.1
LABEL org.opencontainers.image.title="runner-ci-web-e2e" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.stack="web-e2e"

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
USER root
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "runner base must be digest-qualified" >&2; exit 1 ;; esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends openssh-client redis-server redis-tools rsync zip \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global "playwright@${AI_REPO_RESOURCES_PLAYWRIGHT_VERSION}" \
    && playwright install --with-deps chromium firefox webkit \
    && chmod -R a+rwX "${PLAYWRIGHT_BROWSERS_PATH}" \
    && npm cache clean --force \
    && playwright --version \
    && redis-server --version
USER runner
