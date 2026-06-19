#!/usr/bin/env bash
#
# Cockpit self-test: compile all modules, run every job, assert each
# portal_data/*.json has its expected keys, and build the dashboard. Use after
# changes or after `jf auth` to confirm the whole pipeline is healthy.
#
#   ./scripts/selftest.sh
#
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY="python3"
cd "$REPO"
fail=0

echo "==> compile"
"$PY" -m py_compile cockpit/*.py cockpit/jobs/*.py && echo "   ok" || { echo "   FAIL"; fail=1; }

echo "==> run all jobs"
for m in brief inbox meeting_prep wrap top_of_mind workplace_digest notifications doc_actions; do
  if "$PY" -m "cockpit.jobs.$m" >/dev/null 2>&1; then echo "   $m ok"; else echo "   $m FAIL"; fail=1; fi
done

echo "==> validate JSON shapes"
"$PY" - <<'PY' || fail=1
import json, sys
from pathlib import Path
DATA = Path("portal_data")
expect = {
    "brief":        ["headline", "agenda"],
    "inbox":        ["unread_count", "priority"],
    "meetings":     ["next_meeting"],
    "wrap":         ["recap", "tomorrow"],
    "workplace":    ["draft"],
    "digest":       ["summary", "key_updates"],
    "notifications":["action_count", "actions"],
    "actions":      ["actions", "decisions"],
}
bad = 0
for name, keys in expect.items():
    p = DATA / f"{name}.json"
    if not p.exists():
        print(f"   {name}.json MISSING"); bad += 1; continue
    d = json.loads(p.read_text())
    missing = [k for k in keys if k not in d]
    print(f"   {name}.json " + ("ok" if not missing else f"MISSING {missing}"))
    bad += bool(missing)
sys.exit(1 if bad else 0)
PY

echo "==> build dashboard"
"$PY" -m cockpit.build_cockpit >/dev/null 2>&1 && echo "   ok" || { echo "   FAIL"; fail=1; }

echo ""
[ "$fail" = 0 ] && echo "✅ selftest passed" || { echo "❌ selftest had failures"; exit 1; }
