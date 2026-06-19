#!/usr/bin/env bash
#
# Build the Cockpit Portal app, install it on a USB-connected Portal, and launch
# it. Run this once, and again whenever you change the app itself (Java/manifest).
# For a content-only update after the jobs run, use ./refresh.sh (no rebuild).
#
# The APK is built WITHOUT Gradle (see build_apk.sh) — plain Java, no deps —
# which is fast and avoids Gradle's daemon. Set USE_GRADLE=1 to use ./gradlew.
#
# Prereqs (one-time): see README.md
#   - Portal connected via USB-C with "ADB Enabled" (Settings -> Debug)
#   - android-platform-tools (adb) installed
#   - Android SDK (auto-detected at ~/Library/Android/sdk) and a JDK
#     (auto-detected from Android Studio's bundled JBR)
#
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

PKG="com.josephine.cockpit"
ACT="$PKG/.MainActivity"
ADB="${ADB:-/usr/local/platform-tools/adb}"
command -v adb >/dev/null 2>&1 && ADB="$(command -v adb)"

echo "==> [1/3] Building APK (generates dashboard first) ..."
if [ "${USE_GRADLE:-0}" = "1" ] && [ -x ./gradlew ]; then
  ( cd .. && python3 -m cockpit.build_cockpit )
  ./gradlew assembleDebug
  APK="app/build/outputs/apk/debug/app-debug.apk"
else
  ./build_apk.sh
  APK="manual_build/cockpit-debug.apk"
fi

echo "==> [2/3] Checking for a connected Portal ..."
"$ADB" get-state >/dev/null 2>&1 || { echo "ERROR: no device via adb. Connect the Portal over USB-C and enable ADB (Settings -> Debug)."; exit 1; }

echo "==> [3/3] Installing + launching on Portal ..."
"$ADB" install -r "$APK"
# Drop any quick-refresh override so the freshly bundled dashboard is shown.
"$ADB" shell rm -f "/sdcard/Android/data/$PKG/files/dashboard/index.html" 2>/dev/null || true
"$ADB" shell am start -n "$ACT"

echo ""
echo "Done. 'Cockpit' is installed and running on your Portal."
