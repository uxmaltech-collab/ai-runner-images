# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.title="runner-resolver-cx-chatbot-app" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.profile="resolver-cx-chatbot-app" \
      io.enviaflores.runner.engine="codex"

USER root
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "Agent base must be digest-qualified" >&2; exit 1 ;; esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      composer openssh-client redis-server rsync zip \
      php-bcmath php-cli php-curl php-intl php-mbstring php-mysql php-redis php-sqlite3 php-xml php-zip \
    && rm -rf /var/lib/apt/lists/* \
    && codex --version \
    && php --version \
    && composer --version \
    && redis-server --version
USER runner
