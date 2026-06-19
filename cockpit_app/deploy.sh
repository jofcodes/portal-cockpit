#!/usr/bin/env bash
#
# Build the Cockpit Portal app, install it on a USB-connected Portal, and launch
# it. Run this once, and again whenever you change the app itself (Java/manifest).
# For a content-only update after the jobs run, use ./refresh.sh (no rebuild).
#
# Prereqs (one-time): see README.md
#   - Portal connected via USB-C with "ADB Enabled" (Settings -> Debug)
#   - android-platform-tools (adb) installed
#   - Android SDK (this script auto-detects ~/Library/Android/sdk) and a JDK 17+
#     (this script auto-detects the Android Studio bundled JBR)
#
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
cd "$HERE"

PKG="com.josephine.cockpit"
ACT="$PKG/.MainActivity"
ADB="${ADB:-/usr/local/platform-tools/adb}"
command -v adb >/dev/null 2>&1 && ADB="$(command -v adb)"

# --- toolchain auto-config -------------------------------------------------
# JDK: prefer an explicit JAVA_HOME, else Android Studio's bundled JBR.
if [ -z "${JAVA_HOME:-}" ]; then
  JBR="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  [ -x "$JBR/bin/java" ] && export JAVA_HOME="$JBR"
fi
# Android SDK location for Gradle.
SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Library/Android/sdk}}"
if [ -d "$SDK" ] && [ ! -f local.properties ]; then
  echo "sdk.dir=$SDK" > local.properties
fi

echo "==> [1/4] Generating dashboard from the latest portal_data/ ..."
( cd "$REPO" && python3 -m cockpit.build_cockpit )

echo "==> [2/4] Building debug APK ..."
if [ -x ./gradlew ]; then
  ./gradlew assembleDebug
else
  command -v gradle >/dev/null || { echo "ERROR: no ./gradlew and no 'gradle' on PATH. Open this folder in Android Studio once, or run 'gradle wrapper'."; exit 1; }
  gradle assembleDebug
fi
APK="app/build/outputs/apk/debug/app-debug.apk"

echo "==> [3/4] Checking for a connected Portal ..."
"$ADB" get-state >/dev/null 2>&1 || { echo "ERROR: no device via adb. Connect the Portal over USB-C and enable ADB (Settings -> Debug)."; exit 1; }

echo "==> [4/4] Installing + launching on Portal ..."
"$ADB" install -r "$APK"
# Drop any quick-refresh override so the freshly bundled dashboard is shown.
"$ADB" shell rm -f "/sdcard/Android/data/$PKG/files/dashboard/index.html" 2>/dev/null || true
"$ADB" shell am start -n "$ACT"

echo ""
echo "Done. 'Cockpit' is installed and running on your Portal."
