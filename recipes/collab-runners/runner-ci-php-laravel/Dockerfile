# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.title="runner-ci-php-laravel" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.stack="php-laravel"

USER root
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "runner base must be digest-qualified" >&2; exit 1 ;; esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      composer openssh-client redis-server rsync zip \
      php-bcmath php-cli php-curl php-gd php-intl php-mbstring php-mysql php-pgsql \
      php-pcov php-redis php-sqlite3 php-xml php-zip \
    && rm -rf /var/lib/apt/lists/* \
    && php --version \
    && php -m | grep -qx pcov \
    && composer --version \
    && redis-server --version
USER runner
