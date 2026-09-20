# syntax=docker/dockerfile:1.7
ARG RUNNER_BASE_IMAGE
ARG PYTHON_BASE_IMAGE
FROM ${RUNNER_BASE_IMAGE} AS tools
FROM ${PYTHON_BASE_IMAGE}
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git openssh-client \
    && rm -rf /var/lib/apt/lists/*
COPY --from=tools /usr/local/bin/docker /usr/local/bin/docker
ARG SOURCE_REVISION
ARG RUNTIME_COMMIT
LABEL org.opencontainers.image.title="Collab Python runner control plane" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      io.collab.runtime.commit="${RUNTIME_COMMIT}"
COPY collab-release /opt/collab-release
RUN python /opt/collab-release/install.py install \
      --artifacts /opt/collab-release --prefix /opt/collab/runtime \
    && /opt/collab/runtime/bin/python -I -c 'import collab_runners.controlplane' \
    && git --version \
    && ssh -V
ENV PATH="/opt/collab/runtime/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    COLLAB_REPO_PACK=/etc/collab/repo-pack
VOLUME ["/var/lib/runner-control-plane"]
EXPOSE 8080
CMD ["/opt/collab/runtime/bin/python", "-I", "-m", "collab_runners.controlplane"]
