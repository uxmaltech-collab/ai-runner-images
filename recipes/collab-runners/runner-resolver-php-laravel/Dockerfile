# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

LABEL org.opencontainers.image.title="runner-resolver-php-laravel" \
      collab.runner.profile="resolver-php-laravel"

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      composer openssh-client redis-server rsync zip \
      php-bcmath php-cli php-curl php-gd php-intl php-mbstring php-mysql php-pgsql \
      php-redis php-sqlite3 php-xml php-zip \
    && rm -rf /var/lib/apt/lists/* \
    && codex --version \
    && php --version \
    && composer --version \
    && redis-server --version
USER runner

# The image carries no Collab runtime. At job start the control plane mounts the host's verified
# runtime read-only, exports COLLAB_RUNTIME=<path>@sha256:<digest> and puts its bin first on PATH, so a
# Collab release rebuilds no image. The pack revision changes with every publication, so it is declared
# last, and the parent digest is never redeclared inside a stage: a pack change rebuilds nothing.
ENV ARCHIFY_UPDATE_CHECK_DISABLED=1
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}"
USER runner
