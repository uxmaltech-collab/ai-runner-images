# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.title="runner-resolver-airflow-dag" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.profile="resolver-airflow-dag" \
      io.enviaflores.runner.engine="codex"

USER root
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "Agent base must be digest-qualified" >&2; exit 1 ;; esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends fd-find make \
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --break-system-packages --no-cache-dir \
      "pytest==9.1.1" "PyYAML>=6.0,<7" "jinja2>=3.1,<4" \
    && codex --version \
    && pytest --version \
    && actionlint --version
USER runner
