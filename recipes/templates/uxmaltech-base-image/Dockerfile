# syntax=docker/dockerfile:1.7
# uxmaltech-base-image — the PHP runtime base of every uxmaltech PHP flavor.
#
# Built FROM a digest-pinned agent-base (the harness-complete root of every
# lineage), it transplants the FrankenPHP runtime — the same PHP build the
# organization's production sites run — from the official FrankenPHP image of
# the same Debian release, then installs the shared extension set the
# backoffice-ui and backend-cbq packages require. Flavors extend this image
# per repository type and add the organization's pack CLI and the repository's
# stack; nothing repository-specific and no credential lives here.
#
# Every input is pinned: the parent arrives as a registry digest or an
# image-id tag, and the donor images are digest-qualified.
ARG AGENT_BASE_IMAGE=ghcr.io/example-org/agent-base@sha256:0000000000000000000000000000000000000000000000000000000000000000
ARG FRANKENPHP_IMAGE=docker.io/dunglas/frankenphp:1.10.1-php8.4-trixie@sha256:4c771707d56ccbe2df9e0df8c00426249aa1f96485ff00959a65764d031e7cf7
ARG COMPOSER_IMAGE=docker.io/library/composer:2@sha256:4d71c3c2109c61d5415544264b59ad4087e4c5b7244481723664138fd36d5040
FROM ${FRANKENPHP_IMAGE} AS frankenphp
FROM ${COMPOSER_IMAGE} AS composer
FROM ${AGENT_BASE_IMAGE}

ARG AGENT_BASE_IMAGE
ARG UXMALTECH_BASE_REVISION=unknown
ARG RDKAFKA_VERSION=6.0.5

LABEL org.opencontainers.image.title="uxmaltech-base-image" \
      org.opencontainers.image.description="FrankenPHP runtime base of the uxmaltech PHP flavors: PHP 8.4, the shared backoffice-ui/backend-cbq extension set and Composer on the harness-complete agent-base." \
      org.opencontainers.image.revision="${UXMALTECH_BASE_REVISION}" \
      io.uxmaltech.agent.lineage="agent-base,uxmaltech-base-image" \
      io.uxmaltech.agent.stack="php-frankenphp"

# The transplanted runtime keeps the donor image's configuration root.
ENV PHP_INI_DIR=/usr/local/etc/php

USER root
# Same-OS transplant: agent-base and the FrankenPHP donor share the same
# Debian release, so the /usr/local PHP runtime (php, pecl, pear, phpize,
# php-config, docker-php-ext-*, install-php-extensions, frankenphp) drops in
# beside the Node.js toolchain without a collision, and /usr/local/bin/php
# shadows nothing: no apt php is ever installed in this lineage.
RUN case "${AGENT_BASE_IMAGE}" in *@sha256:*|*:id-*) ;; \
      *) echo "AGENT_BASE_IMAGE must be a registry digest or an image-id tag" >&2; exit 1 ;; esac
COPY --from=frankenphp /usr/local/bin/ /usr/local/bin/
COPY --from=frankenphp /usr/local/lib/php/ /usr/local/lib/php/
# Every shared library the donor runtime carries (libphp, libwatcher-c, ...):
# the frankenphp binary links against them; the linker cache follows below.
COPY --from=frankenphp /usr/local/lib/*.so* /usr/local/lib/
COPY --from=frankenphp /usr/local/etc/ /usr/local/etc/
COPY --from=frankenphp /usr/local/include/php/ /usr/local/include/php/
# The PHP source tarball: docker-php-ext-install compiles extensions from it.
COPY --from=frankenphp /usr/src/ /usr/src/
COPY --from=composer /usr/bin/composer /usr/local/bin/composer
RUN ldconfig

# Runtime shared libraries the donor's PHP links against, from this release's
# own apt universe.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libargon2-1 libcurl4 libedit2 libonig5 libsodium23 libsqlite3-0 \
      libxml2 libzip5 rsync zip \
    && rm -rf /var/lib/apt/lists/*

# The shared extension set of the organization's PHP production runtime
# (backoffice-ui and backend-cbq consumers), exactly as the production site
# image installs it, plus rdkafka from pecl at an exact version. Build inputs
# are purged; only the runtime library stays.
RUN install-php-extensions pdo_mysql zip pcntl bcmath intl opcache redis opentelemetry \
    && apt-get update \
    && apt-get install -y --no-install-recommends autoconf pkg-config librdkafka-dev \
    && pecl install "rdkafka-${RDKAFKA_VERSION}" \
    && docker-php-ext-enable rdkafka \
    && apt-get purge -y --auto-remove autoconf librdkafka-dev \
    && apt-get update \
    && apt-get install -y --no-install-recommends librdkafka1 \
    && rm -rf /var/lib/apt/lists/* /tmp/pear

# The transplant is only healthy when /usr/local/bin/php is the one php, the
# extension set answers, FrankenPHP and Composer run, and no apt php exists.
RUN command -v php | grep -Fx /usr/local/bin/php \
    && php --version | grep -F "PHP 8.4" \
    && php -m | grep -ix rdkafka \
    && php -m | grep -ix redis \
    && php -m | grep -ix pcntl \
    && frankenphp version \
    && composer --version \
    && ! dpkg -l 'php*' 2>/dev/null | grep -q '^ii' \
    && claude --version >/dev/null

USER agent
