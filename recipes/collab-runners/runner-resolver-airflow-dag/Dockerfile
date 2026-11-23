# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

LABEL org.opencontainers.image.title="runner-resolver-airflow-dag" \
      collab.runner.profile="resolver-airflow-dag"

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends fd-find make \
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-cache-dir \
      "pytest==9.1.1" "PyYAML>=6.0,<7" "jinja2>=3.1,<4" \
    && codex --version \
    && pytest --version \
    && actionlint --version
USER runner

# The image carries no Collab runtime. At job start the control plane mounts the host's verified
# runtime read-only, exports COLLAB_RUNTIME=<path>@sha256:<digest> and puts its bin first on PATH, so a
# Collab release rebuilds no image. The pack revision changes with every publication, so it is declared
# last, and the parent digest is never redeclared inside a stage: a pack change rebuilds nothing.
ENV ARCHIFY_UPDATE_CHECK_DISABLED=1
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}"
USER runner
