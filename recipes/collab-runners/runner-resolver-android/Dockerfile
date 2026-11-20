# syntax=docker/dockerfile:1.7
# The resolver and journey runner for an Android application. It adds to the neutral
# Android layer (recipes/android, released once as the recipe `android`) only what is
# specific to a resolver: the journey binding, the helper aliases and the Collab
# runtime. The toolchain lock, the emulator registration, the helpers and the
# entrypoint are not repeated here: they come from the parent.
ARG RUNNER_ANDROID_IMAGE
FROM ${RUNNER_ANDROID_IMAGE}

ARG RUNNER_ANDROID_IMAGE
# Plan-time inputs. The planner resolves them from the organization's canon and passes
# them as build arguments; this recipe carries no organization value. Without them the
# prior verified journey binding stays in the image and the build warns (see
# common/plan-inputs.py). RUNNER_HELPER_ALIASES is a list of ALIAS=TARGET pairs for the
# former helper paths, and RUNNER_ANDROID_MARKER_ALIASES a list of former emulator
# ownership-marker names, that a consumer still reads during its migration.
ARG RUNNER_JOURNEY_REPOSITORY=
ARG RUNNER_JOURNEY_PROFILE=
ARG RUNNER_JOURNEY_VALIDATOR=
ARG RUNNER_HELPER_ALIASES=
ARG RUNNER_ANDROID_MARKER_ALIASES=
ENV RUNNER_ANDROID_EMULATOR_OWNED_ALIASES="${RUNNER_ANDROID_MARKER_ALIASES}"
LABEL org.opencontainers.image.title="runner-resolver-android" \
      collab.runner.profile="resolver-android" \
      collab.runner.stack="android-gradle-maestro"

USER root
RUN case "${RUNNER_ANDROID_IMAGE}" in *@sha256:*) ;; \
      *) echo "The Android layer must be digest-qualified" >&2; exit 1 ;; esac
# The stable neutral helpers are runner-android-emulator and runner-android-stack-probe,
# installed by the parent in /usr/local/bin.
COPY recipes/collab-runners/common/plan-inputs.py /opt/runner-plan-inputs/plan-inputs.py
COPY recipes/collab-runners/runner-resolver-android/journey-driver.json /opt/ai-repo-resources/journey-driver.json
RUN python3 /opt/runner-plan-inputs/plan-inputs.py journey \
      --fallback /opt/ai-repo-resources/journey-driver.json --output /opt/ai-repo-resources/journey-driver.json \
    && python3 /opt/runner-plan-inputs/plan-inputs.py aliases \
    && chmod -R a+rX /opt/ai-repo-resources /opt/runner-plan-inputs

# Collab changes most often, so it is the last layer. The pack revision changes
# with every publication, so it is declared only after it: a Collab release rebuilds
# this layer alone on top of the cached Android layer, and a pack change rebuilds nothing.
USER root
COPY collab-release /opt/collab-release
RUN python3.12 /opt/collab-release/install.py install --artifacts /opt/collab-release --prefix /opt/collab/runtime \
    && /opt/collab/runtime/bin/collab --version
ENV PATH="/opt/collab/runtime/bin:${PATH}" \
    ARCHIFY_PUBLISH_PYTHON=/opt/collab/runtime/bin/python \
    ARCHIFY_UPDATE_CHECK_DISABLED=1
ARG AI_REPO_RESOURCES_BUNDLE_COMMIT
LABEL org.opencontainers.image.revision="${AI_REPO_RESOURCES_BUNDLE_COMMIT}"

# The parent's entrypoint adds only the mapped device group and immediately execs the
# inherited /entrypoint.sh as UID/GID 1001, preserving no-new-privileges; it starts as root.
USER root
