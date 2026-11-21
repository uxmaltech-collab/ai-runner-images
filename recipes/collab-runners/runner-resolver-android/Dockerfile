# syntax=docker/dockerfile:1.7
# The resolver and journey runner for an Android application. It adds to the neutral
# Android layer (recipes/android, released once as the recipe `android`) only what is
# specific to a resolver: the journey binding, the helper aliases and the Collab
# runtime. The toolchain lock, the emulator registration, the helpers and the
# entrypoint are not repeated here: they come from the parent.
ARG RUNNER_ANDROID_IMAGE
FROM ${RUNNER_ANDROID_IMAGE}

ARG RUNNER_ANDROID_IMAGE
# Plan-time inputs. The planner resolves them from the organization's canon (or from its
# own last verified read of it) and passes them as build arguments; this recipe carries no
# organization value. Without them the image is built without a journey binding and the
# build warns (see common/plan-inputs.py): nothing is kept from, or invented for, any
# organization. RUNNER_HELPER_ALIASES is a list of ALIAS=TARGET pairs for the former helper
# paths, and RUNNER_ANDROID_MARKER_ALIASES a list of former emulator ownership-marker
# names, that a consumer still reads during its migration.
ARG RUNNER_JOURNEY_REPOSITORY=
ARG RUNNER_JOURNEY_PROFILE=
ARG RUNNER_JOURNEY_VALIDATOR=
ARG RUNNER_HELPER_ALIASES=
ARG RUNNER_ANDROID_MARKER_ALIASES=
# The approved digest of the Android layer (the canon's image pin) and, optionally, the digest
# the builder observed. The reference itself must be <image>@sha256:<digest>: a tag is
# mutable and stops the build, and so does a digest that is not the approved one.
ARG RUNNER_ANDROID_IMAGE_DIGEST=
ARG RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST=
LABEL org.opencontainers.image.title="runner-resolver-android" \
      collab.runner.profile="resolver-android" \
      collab.runner.stack="android-gradle-maestro"

USER root
# The stable neutral helpers are runner-android-emulator and runner-android-stack-probe,
# installed by the parent in /usr/local/bin.
COPY recipes/collab-runners/common/plan-inputs.py /opt/runner-plan-inputs/plan-inputs.py
COPY recipes/collab-runners/runner-resolver-android/journey-driver.json /opt/runner-plan-inputs/journey-driver.template.json
# Each step warns and goes on, except the first when the Android layer is another artifact
# than the approved one. The marker aliases go to an image-owned file because the journey
# launcher starts the emulator helper with a fixed list of environment variables.
RUN python3 /opt/runner-plan-inputs/plan-inputs.py parent \
      --reference "${RUNNER_ANDROID_IMAGE}" --approved "${RUNNER_ANDROID_IMAGE_DIGEST}" \
      --resolved "${RUNNER_ANDROID_IMAGE_RESOLVED_DIGEST}" \
    && mkdir -p /opt/ai-repo-resources \
    && python3 /opt/runner-plan-inputs/plan-inputs.py journey \
      --template /opt/runner-plan-inputs/journey-driver.template.json --output /opt/ai-repo-resources/journey-driver.json \
    && python3 /opt/runner-plan-inputs/plan-inputs.py aliases \
    && python3 /opt/runner-plan-inputs/plan-inputs.py markers \
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
