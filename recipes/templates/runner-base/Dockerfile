# syntax=docker/dockerfile:1.7
# runner-base — the toolchain-complete base image of every ephemeral GitHub
# Actions runner the control plane spawns (JIT-registered, one job, --rm).
#
# Nothing organization-specific lives here: the OS base image, tool versions,
# digests, build context paths, and the JIT-config environment variable name
# are all build arguments a consumer pins from its own pack. Flavor images
# extend this per repository type and stay consumer-owned.
ARG RUNNER_BASE_OS_IMAGE
FROM ${RUNNER_BASE_OS_IMAGE}

ARG RUNNER_BASE_OS_IMAGE
ARG RUNNER_BASE_REVISION
ARG ACTIONS_RUNNER_VERSION=2.335.1
ARG ACTIONS_RUNNER_SHA256_AMD64
ARG ACTIONS_RUNNER_SHA256_ARM64
ARG ACTIONLINT_VERSION=1.7.7
ARG ACTIONLINT_SHA256_AMD64
ARG ACTIONLINT_SHA256_ARM64
ARG GH_VERSION=2.96.0
ARG GH_SHA256_AMD64=83d5c2ccad5498f58bf6368acb1ab32588cf43ab3a4b1c301bf36328b1c8bd60
ARG GH_SHA256_ARM64=06f86ec7103d41993b76cd78072f43595c34aaa56506d971d9860e67140bf909
ARG DOCKER_CLI_VERSION=27.5.1
ARG DOCKER_CLI_SHA256_AMD64
ARG DOCKER_CLI_SHA256_ARM64
ARG RUNNER_BASE_CONTEXT=containers/runner-base
ARG JIT_CONFIG_ENV=RUNNERS_PACK_JIT_CONFIG
ARG TARGETARCH

LABEL org.opencontainers.image.title="runner-base" \
      org.opencontainers.image.revision="${RUNNER_BASE_REVISION}" \
      io.uxmaltech.runner.lineage="runner-base"

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/home/runner/.local/bin:${PATH}"

RUN case "${RUNNER_BASE_OS_IMAGE}" in *@sha256:*) ;; \
      *) echo "RUNNER_BASE_OS_IMAGE must be digest-qualified" >&2; exit 1 ;; esac \
    && test -n "${RUNNER_BASE_REVISION}" \
    && test -n "${ACTIONS_RUNNER_SHA256_AMD64}" \
    && test -n "${ACTIONS_RUNNER_SHA256_ARM64}" \
    && test -n "${ACTIONLINT_SHA256_AMD64}" \
    && test -n "${ACTIONLINT_SHA256_ARM64}" \
    && test -n "${DOCKER_CLI_SHA256_AMD64}" \
    && test -n "${DOCKER_CLI_SHA256_ARM64}" \
    && case "${JIT_CONFIG_ENV}" in ''|[0-9]*|*[!A-Z0-9_]*) echo "JIT_CONFIG_ENV must be an uppercase environment variable name" >&2; exit 1 ;; esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential ca-certificates curl git jq less nodejs npm python3 python3-pip python3-venv \
      ripgrep shellcheck sudo tar unzip xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 runner \
    && useradd --uid 1001 --gid 1001 --create-home --shell /bin/bash runner \
    && echo "runner ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/runner \
    && chmod 0440 /etc/sudoers.d/runner \
    && mkdir -p /actions-runner/_work \
    && chown -R runner:runner /actions-runner

RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
      amd64) tool_arch=amd64; docker_arch=x86_64; gh_sha="${GH_SHA256_AMD64}"; actionlint_sha="${ACTIONLINT_SHA256_AMD64}"; docker_sha="${DOCKER_CLI_SHA256_AMD64}" ;; \
      arm64) tool_arch=arm64; docker_arch=aarch64; gh_sha="${GH_SHA256_ARM64}"; actionlint_sha="${ACTIONLINT_SHA256_ARM64}"; docker_sha="${DOCKER_CLI_SHA256_ARM64}" ;; \
      *) echo "unsupported tool architecture" >&2; exit 1 ;; \
    esac; \
    curl -fsSL \
      "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_${tool_arch}.tar.gz" \
      -o /tmp/actionlint.tar.gz; \
    echo "${actionlint_sha}  /tmp/actionlint.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/actionlint.tar.gz -C /usr/local/bin actionlint; \
    curl -fsSL \
      "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${tool_arch}.tar.gz" \
      -o /tmp/gh.tar.gz; \
    echo "${gh_sha}  /tmp/gh.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/gh.tar.gz -C /tmp; \
    install -m 0755 "/tmp/gh_${GH_VERSION}_linux_${tool_arch}/bin/gh" /usr/local/bin/gh; \
    curl -fsSL \
      "https://download.docker.com/linux/static/stable/${docker_arch}/docker-${DOCKER_CLI_VERSION}.tgz" \
      -o /tmp/docker.tar.gz; \
    echo "${docker_sha}  /tmp/docker.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/docker.tar.gz -C /usr/local/bin --strip-components=1 docker/docker; \
    rm -rf /tmp/actionlint.tar.gz /tmp/docker.tar.gz /tmp/gh.tar.gz "/tmp/gh_${GH_VERSION}_linux_${tool_arch}"; \
    actionlint --version; \
    docker --version; \
    gh --version; \
    node --version; \
    npm --version

WORKDIR /actions-runner

RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
      amd64) runner_arch=x64; runner_sha="${ACTIONS_RUNNER_SHA256_AMD64}" ;; \
      arm64) runner_arch=arm64; runner_sha="${ACTIONS_RUNNER_SHA256_ARM64}" ;; \
      *) echo "unsupported Actions Runner architecture" >&2; exit 1 ;; \
    esac; \
    curl -fsSL \
      "https://github.com/actions/runner/releases/download/v${ACTIONS_RUNNER_VERSION}/actions-runner-linux-${runner_arch}-${ACTIONS_RUNNER_VERSION}.tar.gz" \
      -o /tmp/actions-runner.tar.gz; \
    echo "${runner_sha}  /tmp/actions-runner.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/actions-runner.tar.gz -C /actions-runner; \
    rm -f /tmp/actions-runner.tar.gz; \
    chown -R runner:runner /actions-runner; \
    test -x /actions-runner/run.sh

COPY --chown=runner:runner ${RUNNER_BASE_CONTEXT}/entrypoint-jit.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

ENV JIT_CONFIG_ENV=${JIT_CONFIG_ENV}

USER runner
ENTRYPOINT ["/entrypoint.sh"]
