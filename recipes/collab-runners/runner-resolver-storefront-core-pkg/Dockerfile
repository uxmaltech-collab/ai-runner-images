# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE} AS php-build

ARG PHP_VERSION=8.3.33
ARG PHP_SOURCE_SHA256
ARG PHP_REDIS_VERSION=6.3.0
ARG PHP_REDIS_SHA256
ARG COMPOSER_VERSION=2.9.5
ARG COMPOSER_SHA256

USER root
# Build the supported PHP minor independently of the base OS's default PHP.
# No third-party apt repository or additional container base is involved.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      autoconf build-essential pkg-config libcurl4-openssl-dev libicu-dev \
      libonig-dev libsqlite3-dev libssl-dev libxml2-dev libzip-dev zlib1g-dev \
    && curl -fsSL "https://www.php.net/distributions/php-${PHP_VERSION}.tar.xz" -o /tmp/php.tar.xz \
    && echo "${PHP_SOURCE_SHA256}  /tmp/php.tar.xz" | sha256sum -c - \
    && mkdir /tmp/php-source \
    && tar -xJf /tmp/php.tar.xz --strip-components=1 -C /tmp/php-source \
    && cd /tmp/php-source \
    && ./configure --prefix=/opt/php --with-config-file-path=/opt/php/etc \
      --with-config-file-scan-dir=/opt/php/etc/conf.d --disable-cgi --disable-phpdbg \
      --without-pear --with-openssl --with-zlib --with-curl --enable-bcmath \
      --enable-intl --enable-mbstring --enable-pcntl --with-pdo-sqlite \
      --with-sqlite3 --with-zip \
    && make -j4 \
    && make install \
    && mkdir -p /opt/php/etc/conf.d \
    && cp php.ini-production /opt/php/etc/php.ini \
    && curl -fsSL "https://pecl.php.net/get/redis-${PHP_REDIS_VERSION}.tgz" -o /tmp/redis.tgz \
    && echo "${PHP_REDIS_SHA256}  /tmp/redis.tgz" | sha256sum -c - \
    && mkdir /tmp/redis-source \
    && tar -xzf /tmp/redis.tgz --strip-components=1 -C /tmp/redis-source \
    && cd /tmp/redis-source \
    && /opt/php/bin/phpize \
    && ./configure --with-php-config=/opt/php/bin/php-config \
    && make -j4 \
    && make install \
    && echo 'extension=redis.so' > /opt/php/etc/conf.d/redis.ini \
    && curl -fsSL "https://getcomposer.org/download/${COMPOSER_VERSION}/composer.phar" -o /opt/php/bin/composer \
    && echo "${COMPOSER_SHA256}  /opt/php/bin/composer" | sha256sum -c - \
    && chmod 0755 /opt/php/bin/composer

FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}
LABEL org.opencontainers.image.title="runner-resolver-storefront-core-pkg" \
      io.enviaflores.runner.profile="resolver-storefront-core-pkg" \
      io.enviaflores.runner.engine="codex"

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      openssh-client rsync zip libcurl4t64 libicu78 libonig5 libsqlite3-0 \
      libssl3t64 libxml2-16 libzip5 zlib1g \
    && rm -rf /var/lib/apt/lists/*
COPY --from=php-build /opt/php /opt/php
# Login shells used by the harness reset PATH; expose the same PHP there too.
RUN ln -sfnT /opt/php/bin/php /usr/local/bin/php \
    && ln -sfnT /opt/php/bin/composer /usr/local/bin/composer
COPY recipes/collab-runners/runner-resolver-storefront-core-pkg/platform-probe.php /opt/php/platform-probe.php
RUN php --version && php /opt/php/platform-probe.php && composer --version && codex --version
USER runner

# Collab changes most often, so it is the last layer. The pack revision changes
# with every publication, so it is declared only after it, and the parent digest
# is never redeclared inside a stage: a Collab release rebuilds this layer alone
# on top of the cached technology stack, and a pack change rebuilds nothing.
USER root
COPY collab-release /opt/collab-release
RUN python3.12 /opt/collab-release/install.py install --artifacts /opt/collab-release --prefix /opt/collab/runtime \
    && /opt/collab/runtime/bin/collab --version
ENV PATH="/opt/collab/runtime/bin:${PATH}" \
    ARCHIFY_PUBLISH_PYTHON=/opt/collab/runtime/bin/python \
    ARCHIFY_UPDATE_CHECK_DISABLED=1
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}"
USER runner
