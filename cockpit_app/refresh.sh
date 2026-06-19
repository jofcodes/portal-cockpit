#!/usr/bin/env bash
#
# Quick refresh: regenerate the Cockpit dashboard from the newest portal_data/
# and push it to the Portal WITHOUT rebuilding/reinstalling the APK. Run
# ./deploy.sh once first (to install the app); after that use this whenever the
# jobs produce new portal_data/*.json.
#
# Pass --jobs to run the data jobs (brief, inbox, wrap) first.
#
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
cd "$HERE"

PKG="com.josephine.cockpit"
DEST_DIR="/sdcard/Android/data/$PKG/files/dashboard"
DEST="$DEST_DIR/index.html"
ADB="${ADB:-/usr/local/platform-tools/adb}"
command -v adb >/dev/null 2>&1 && ADB="$(command -v adb)"
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY="python3"

if [ "${1:-}" = "--jobs" ]; then
  echo "==> Running data jobs (brief, inbox, wrap) ..."
  ( cd "$REPO" && "$PY" -m cockpit.jobs.brief && "$PY" -m cockpit.jobs.inbox && "$PY" -m cockpit.jobs.wrap )
fi

echo "==> Regenerating dashboard ..."
( cd "$REPO" && "$PY" -m cockpit.build_cockpit )

echo "==> Checking for a connected Portal ..."
"$ADB" get-state >/dev/null 2>&1 || { echo "ERROR: no device via adb. Connect the Portal and enable ADB."; exit 1; }

echo "==> Pushing dashboard to Portal ..."
"$ADB" shell mkdir -p "$DEST_DIR" 2>/dev/null || true
if "$ADB" push app/src/main/assets/dashboard/index.html "$DEST"; then
  "$ADB" shell am start -n "$PKG/.MainActivity"
  echo "Refreshed — the Portal is now showing the latest Cockpit."
else
  echo ""
  echo "Push to the app folder was blocked by the device. Fall back to a full"
  echo "rebuild/reinstall instead:  ./deploy.sh"
  exit 1
fi
