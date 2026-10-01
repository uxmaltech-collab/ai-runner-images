# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

LABEL org.opencontainers.image.title="runner-resolver-cx-chatbot-app" \
      io.enviaflores.runner.profile="resolver-cx-chatbot-app" \
      io.enviaflores.runner.engine="codex"

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      composer openssh-client redis-server rsync zip \
      php-bcmath php-cli php-curl php-intl php-mbstring php-mysql php-redis php-sqlite3 php-xml php-zip \
    && rm -rf /var/lib/apt/lists/* \
    && codex --version \
    && php --version \
    && composer --version \
    && redis-server --version
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
