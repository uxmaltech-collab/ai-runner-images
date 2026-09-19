# syntax=docker/dockerfile:1.7
ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
FROM ${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}

ARG AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
ARG TARGETARCH
LABEL org.opencontainers.image.title="runner-resolver-storefront-android" \
      org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
      io.enviaflores.runner.profile="resolver-storefront-android" \
      io.enviaflores.runner.engine="codex" \
      io.enviaflores.runner.stack="android-gradle-maestro"

# One image serves resolve and create-journey. Neither the entrypoint nor a
# resolve job boots an emulator. The journey explicitly invokes the wrapper.
ENV JAVA_HOME=/opt/java \
    ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    MAESTRO_CLI_NO_ANALYTICS=1 \
    MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED=true \
    PATH="/opt/java/bin:/opt/android-sdk/cmdline-tools/19.0/bin:/opt/android-sdk/platform-tools:/opt/android-sdk/emulator:/opt/maestro/bin:${PATH}"

USER root
COPY recipes/collab-runners/runner-resolver-storefront-android/toolchain-lock.json /opt/ef-storefront-android/toolchain-lock.json
COPY recipes/collab-runners/runner-resolver-storefront-android/journey-driver.json /opt/ai-repo-resources/journey-driver.json
COPY recipes/collab-runners/runner-resolver-storefront-android/scripts/install-toolchain.py /opt/ef-storefront-android/install-toolchain.py
COPY recipes/collab-runners/runner-resolver-storefront-android/scripts/ef-storefront-android-emulator.py /usr/local/bin/ef-storefront-android-emulator
COPY recipes/collab-runners/runner-resolver-storefront-android/scripts/ef-storefront-android-stack-probe.sh /usr/local/bin/ef-storefront-android-stack-probe
COPY recipes/collab-runners/runner-resolver-storefront-android/scripts/entrypoint-android.py /usr/local/bin/entrypoint-android
RUN test -n "${AI_REPO_RESOURCES_BUNDLE_COMMIT}" \
    && case "${AI_REPO_RESOURCES_RUNNER_AGENT_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "Agent base must be digest-qualified" >&2; exit 1 ;; esac \
    && test "${TARGETARCH:-$(dpkg --print-architecture)}" = amd64 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      libasound2t64 libdbus-1-3 libfontconfig1 libfreetype6 libgl1 libglu1-mesa \
      libnss3 libpulse0 libx11-6 libxcb1 libxcomposite1 libxcursor1 libxi6 \
      libxkbcommon0 libxkbfile1 libxrandr2 libxtst6 util-linux zip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 /opt/ef-storefront-android/install-toolchain.py \
    && yes | sdkmanager --sdk_root=/opt/android-sdk --licenses >/dev/null
RUN chmod 0755 /usr/local/bin/entrypoint-android /usr/local/bin/ef-storefront-android-emulator /usr/local/bin/ef-storefront-android-stack-probe \
    && chmod -R a+rX /opt/android-sdk /opt/java /opt/maestro /opt/ef-storefront-android
# avdmanager requires this local package registration for a directly installed
# emulator archive; source.properties alone does not register this package.
COPY recipes/collab-runners/runner-resolver-storefront-android/emulator-package.xml /opt/android-sdk/emulator/package.xml
USER runner
# An offline toolchain check; the authorized E2E proves KVM, staging build,
# authentication and the journey. No app sources or credentials enter this image.
RUN --network=none HOME=/home/runner ef-storefront-android-stack-probe
# The bootstrap adds only the mapped device group and immediately execs the
# inherited /entrypoint.sh as UID/GID 1001, preserving no-new-privileges.
USER root
ENTRYPOINT ["/usr/local/bin/entrypoint-android"]
