# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

# SwiftLint ships a statically linked Linux binary; the dynamic one links
# libxml2.so.2, which Ubuntu 26.04 no longer provides (libxml2.so.16).
ARG AI_REPO_RESOURCES_SWIFTLINT_VERSION=0.65.1
ARG AI_REPO_RESOURCES_SWIFTLINT_SHA256_AMD64=caeed6f4a679c35539ffaf124f6c4ab4a8416917f7d8796279dc52b74026059d
ARG TARGETARCH
LABEL org.opencontainers.image.title="runner-resolver-storefront-ios" \
      io.enviaflores.runner.profile="resolver-storefront-ios" \
      io.enviaflores.runner.engine="codex"

USER root
RUN case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
      amd64) swiftlint_sha="${AI_REPO_RESOURCES_SWIFTLINT_SHA256_AMD64}" ;; \
      *) echo "SwiftLint Linux artifact is unavailable for this architecture" >&2; exit 1 ;; esac \
    && curl -fsSL \
      "https://github.com/realm/SwiftLint/releases/download/${AI_REPO_RESOURCES_SWIFTLINT_VERSION}/swiftlint_linux_amd64.zip" \
      -o /tmp/swiftlint.zip \
    && echo "${swiftlint_sha}  /tmp/swiftlint.zip" | sha256sum -c - \
    && unzip -q /tmp/swiftlint.zip -d /tmp/swiftlint \
    && install -m 0755 /tmp/swiftlint/swiftlint-static /usr/local/bin/swiftlint \
    && rm -rf /tmp/swiftlint /tmp/swiftlint.zip \
    && codex --version \
    && swiftlint version | grep -Fx "${AI_REPO_RESOURCES_SWIFTLINT_VERSION}"
USER runner

# journey-driver.json is the native image recipe's iOS build contract. This Linux
# SwiftLint image does not install it; reviewed macos-tart image adoption owns that.

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
