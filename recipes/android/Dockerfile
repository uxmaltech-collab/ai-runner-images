# syntax=docker/dockerfile:1.7
ARG RUNNER_AGENT_BASE_IMAGE
FROM ${RUNNER_AGENT_BASE_IMAGE}

ARG RUNNER_AGENT_BASE_IMAGE
ARG RUNNER_SOURCE_COMMIT
ARG TARGETARCH
LABEL org.opencontainers.image.title="runner-android" \
      org.opencontainers.image.revision="${RUNNER_SOURCE_COMMIT}"

# One image serves resolve and create-journey. Neither the entrypoint nor a
# resolve job boots an emulator. The journey explicitly invokes the wrapper.
ENV JAVA_HOME=/opt/java \
    JAVA21_HOME=/usr/lib/jvm/temurin-21 \
    ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    MAESTRO_CLI_NO_ANALYTICS=1 \
    MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED=true \
    PATH="/opt/java/bin:/opt/android-sdk/cmdline-tools/19.0/bin:/opt/android-sdk/platform-tools:/opt/android-sdk/emulator:/opt/maestro/bin:${PATH}"

USER root
COPY recipes/android/toolchain-lock.json /opt/runner-android/toolchain-lock.json
COPY recipes/android/scripts/install-toolchain.py /opt/runner-android/install-toolchain.py
COPY recipes/android/scripts/runner-android-emulator.py /usr/local/bin/runner-android-emulator
COPY recipes/android/scripts/runner-android-stack-probe.sh /usr/local/bin/runner-android-stack-probe
COPY recipes/android/scripts/entrypoint-android.py /usr/local/bin/entrypoint-android
RUN test -n "${RUNNER_SOURCE_COMMIT}" \
    && case "${RUNNER_AGENT_BASE_IMAGE}" in *@sha256:*) ;; \
      *) echo "Agent base must be digest-qualified" >&2; exit 1 ;; esac \
    && test "${TARGETARCH:-$(dpkg --print-architecture)}" = amd64 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      libasound2t64 libdbus-1-3 libfontconfig1 libfreetype6 libgl1 libglu1-mesa \
      libnss3 libpulse0 libx11-6 libxcb1 libxcomposite1 libxcursor1 libxi6 \
      libxkbcommon0 libxkbfile1 libxrandr2 libxtst6 util-linux zip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 /opt/runner-android/install-toolchain.py \
    && yes | sdkmanager --sdk_root=/opt/android-sdk --licenses >/dev/null
RUN chmod 0755 /usr/local/bin/entrypoint-android /usr/local/bin/runner-android-emulator /usr/local/bin/runner-android-stack-probe \
    && chmod -R a+rX /opt/android-sdk /opt/java /usr/lib/jvm/temurin-21 /opt/maestro /opt/runner-android
# avdmanager requires this local package registration for a directly installed
# emulator archive; source.properties alone does not register this package.
COPY recipes/android/emulator-package.xml /opt/android-sdk/emulator/package.xml
USER runner
# An offline toolchain check; the authorized E2E proves KVM, staging build,
# authentication and the journey. No app sources or credentials enter this image.
RUN --network=none HOME=/home/runner runner-android-stack-probe
# The bootstrap adds only the mapped device group and immediately execs the
# inherited /entrypoint.sh as UID/GID 1001, preserving no-new-privileges.
USER root
ENTRYPOINT ["/usr/local/bin/entrypoint-android"]
