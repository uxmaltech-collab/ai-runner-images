#!/usr/bin/env bash
set -euo pipefail

# No emulator, authentication, downloads or application build in this probe.
java -version 2>&1 | grep -F '17.0.18'
test -f "$ANDROID_HOME/platforms/android-36/android.jar"
test -x "$ANDROID_HOME/build-tools/36.0.0/aapt2"
test -f "$ANDROID_HOME/system-images/android-36/google_apis/x86_64/system.img"
sdkmanager --version | grep -Fx '19.0'
adb version
emulator -version
maestro --version | grep -Fx '2.10.0'
codex --version
command -v setpriv >/dev/null
printf '%s\n' 'Android build and Maestro tools are installed; E2E has not run.'
