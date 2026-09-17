# syntax=docker/dockerfile:1.7
ARG RUNNER_BASE_IMAGE
ARG PYTHON_BASE_IMAGE
FROM ${RUNNER_BASE_IMAGE} AS tools
FROM ${PYTHON_BASE_IMAGE}
ARG SOURCE_REVISION
LABEL org.opencontainers.image.title="portable runner control plane" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
COPY --from=tools /usr/local/bin/docker /usr/local/bin/docker
WORKDIR /opt/runner-pack
COPY wheelhouse /tmp/wheelhouse
COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-index --find-links=/tmp/wheelhouse \
      --require-hashes -r /tmp/requirements.lock \
    && rm -rf /tmp/wheelhouse /tmp/requirements.lock
COPY runners runners
COPY entrypoint.py /opt/runner-pack/entrypoint.py
RUN mkdir -p /var/lib/runner-control-plane
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/opt/runner-pack/entrypoint.py"]
