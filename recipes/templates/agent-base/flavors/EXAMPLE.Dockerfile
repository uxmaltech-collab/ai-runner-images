# syntax=docker/dockerfile:1.7
# A flavor: one repository type's session image, built by the consuming
# organization on top of a digest-pinned agent-base it published itself.
# It inherits the installed Collab runtime and adds the repository's stack. It never
# changes which harnesses exist: all three come from the base.
# AGENT_BASE_IMAGE is the base's registry reference (<image>@sha256:...) or, for
# a base the host built itself, its image-id tag (<image>:id-<12 hex>).
ARG AGENT_BASE_IMAGE=ghcr.io/example-org/agent-base@sha256:0000000000000000000000000000000000000000000000000000000000000000
FROM ${AGENT_BASE_IMAGE}

ARG AGENT_BASE_IMAGE
ARG FLAVOR_REVISION=unknown
LABEL org.opencontainers.image.title="agent-example-service" \
      org.opencontainers.image.revision="${FLAVOR_REVISION}" \
      io.uxmaltech.agent.lineage="agent-base,agent-example-service" \
      io.uxmaltech.agent.stack="php-composer"

USER root
RUN case "${AGENT_BASE_IMAGE}" in *@sha256:*|*:id-*) ;; \
      *) echo "AGENT_BASE_IMAGE must be a registry digest or an image-id tag" >&2; exit 1 ;; esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends composer php-cli php-mbstring php-xml \
    && rm -rf /var/lib/apt/lists/*

# Collab is inherited from the parent image. Mount declarative resources at runtime.

USER agent
