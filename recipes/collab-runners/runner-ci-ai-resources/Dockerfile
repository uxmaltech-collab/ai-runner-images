# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.title="runner-ci-ai-resources" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.profile="ci-ai-resources"

USER root
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "runner base must be digest-qualified" >&2; exit 1 ;; esac \
    && python3 -m pip install --break-system-packages --no-cache-dir \
      "pytest==9.1.1" "PyYAML>=6.0,<7" "ruff==0.9.6" "black==25.1.0" \
    && pytest --version \
    && ruff --version \
    && black --version \
    && shellcheck --version \
    && actionlint --version
USER runner
