#!/usr/bin/env bash
#
# Cockpit scheduled job runner. Runs the right automations for a slot, then
# rebuilds the dashboard. The always-on Cockpit server renders fresh on every
# load, so updated portal_data/*.json shows up on the Portal automatically; if
# the native app is installed, this also refreshes its bundled asset.
#
# Usage: cockpit_job.sh <morning|eod|monday|all>
#
set -euo pipefail
SLOT="${1:-morning}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY="python3"
cd "$REPO"

run() { echo "==> $*"; "$PY" -m "$@"; }

case "$SLOT" in
  morning)  run cockpit.jobs.brief; run cockpit.jobs.inbox; run cockpit.jobs.meeting_prep ;;
  eod)      run cockpit.jobs.wrap ;;
  monday)   run cockpit.jobs.top_of_mind ;;
  all)      run cockpit.jobs.brief; run cockpit.jobs.inbox; run cockpit.jobs.meeting_prep; run cockpit.jobs.wrap ;;
  *) echo "Unknown slot: $SLOT (use morning|eod|monday|all)"; exit 1 ;;
esac

echo "==> rebuild dashboard"
"$PY" -m cockpit.build_cockpit

# If the native Cockpit app is installed on a connected Portal, push the fresh
# dashboard to it (no rebuild). Harmless no-op when the app isn't installed.
ADB="${ADB:-/usr/local/platform-tools/adb}"
if command -v adb >/dev/null 2>&1; then ADB="$(command -v adb)"; fi
if [ -x "$ADB" ] && "$ADB" get-state >/dev/null 2>&1; then
  DEST="/sdcard/Android/data/com.josephine.cockpit/files/dashboard"
  if "$ADB" shell pm list packages 2>/dev/null | grep -q com.josephine.cockpit; then
    "$ADB" shell mkdir -p "$DEST" 2>/dev/null || true
    "$ADB" push cockpit_app/app/src/main/assets/dashboard/index.html "$DEST/index.html" >/dev/null 2>&1 \
      && echo "==> pushed to Portal app" || true
  fi
fi
echo "Cockpit $SLOT job done."
