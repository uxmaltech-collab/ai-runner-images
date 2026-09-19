# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
# SwiftLint ships a statically linked Linux binary; the dynamic one links
# libxml2.so.2, which Ubuntu 26.04 no longer provides (libxml2.so.16).
ARG AI_REPO_RESOURCES_SWIFTLINT_VERSION=0.65.1
ARG AI_REPO_RESOURCES_SWIFTLINT_SHA256_AMD64=caeed6f4a679c35539ffaf124f6c4ab4a8416917f7d8796279dc52b74026059d
ARG TARGETARCH
LABEL org.opencontainers.image.title="runner-resolver-storefront-ios" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.profile="resolver-storefront-ios" \
      io.enviaflores.runner.engine="codex"

USER root
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "Agent base must be digest-qualified" >&2; exit 1 ;; esac \
    && case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
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
