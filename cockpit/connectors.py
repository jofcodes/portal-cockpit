"""Connectors — read work signals via the `meta google.*` CLI.

Each function shells out to `meta`, requests JSON, and returns parsed Python.
When the CLI isn't authenticated (no `jf auth` token), calls raise
`NotAuthenticated`; jobs catch this and fall back to sample fixtures so the
Cockpit can still be built and demoed.

Outbound actions (draft replies) create Gmail DRAFTS only — never send.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import date, datetime, time, timedelta

log = logging.getLogger("cockpit.connectors")

META = shutil.which("meta") or "/opt/facebook/bin/meta"


class MetaCLIError(RuntimeError):
    pass


class NotAuthenticated(MetaCLIError):
    """Raised when the meta CLI has no valid Google Workspace OAuth token."""


def _run(args: list[str], timeout: int = 60) -> str:
    """Run `meta <args>` and return stdout, raising on auth/other failures."""
    cmd = [META, *args]
    log.debug("meta %s", " ".join(args))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    combined = (proc.stdout or "") + (proc.stderr or "")
    if "no OAuth token found" in combined or "OAuth is required" in combined or "No valid Crypto Auth Tokens" in combined:
        raise NotAuthenticated(
            "meta CLI is not authenticated — run `jf auth` "
            "(see https://www.internalfb.com/intern/jf/authenticate/)."
        )
    if proc.returncode != 0:
        raise MetaCLIError(f"`meta {' '.join(args)}` failed: {proc.stderr.strip()[:300]}")
    return proc.stdout


def _unwrap(parsed) -> list[dict]:
    """Normalize meta CLI JSON to a list of records.

    The CLI returns either a bare list (e.g. drive) or a wrapper dict with a
    `data` list + `pagination` (e.g. gmail, calendar). Error responses come back
    as {"status": "error", "message": ...} with returncode 0.
    """
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        if parsed.get("status") == "error":
            raise MetaCLIError(parsed.get("message", "meta CLI error")[:300])
        if isinstance(parsed.get("data"), list):
            return parsed["data"]
        # A single record dict — wrap it.
        return [parsed]
    return []


def _run_json(args: list[str], timeout: int = 60) -> list[dict]:
    """Run a meta command with --output=json and return a list of records."""
    out = _run([*args, "--output=json"], timeout=timeout).strip()
    if not out:
        return []
    try:
        return _unwrap(json.loads(out))
    except json.JSONDecodeError:
        # Some commands print a preamble line before the JSON body.
        start = out.find("[")
        brace = out.find("{")
        if start < 0 or (0 <= brace < start):
            start = brace
        if start >= 0:
            try:
                return _unwrap(json.loads(out[start:]))
            except json.JSONDecodeError:
                pass
        log.warning("Could not parse JSON from: %.200s", out)
        return []


def is_authenticated() -> bool:
    """Cheap probe: try the Gmail profile. Returns False if auth is missing."""
    try:
        _run(["google.gmail.message", "profile"], timeout=30)
        return True
    except NotAuthenticated:
        return False
    except MetaCLIError:
        # Reachable but errored for another reason — treat as "auth ok, try jobs".
        return True


# ── Reads ────────────────────────────────────────────────────────────────

def _normalize_event(e: dict) -> dict:
    """Map a raw calendar record to the shape the jobs/dashboard expect.

    Raw `start` is a full ISO datetime; `attendees` is a comma-separated string
    like "a@x.com (declined), b@y.com (needsAction)".
    """
    raw_start = e.get("start", "")
    when = raw_start
    try:
        when = datetime.fromisoformat(raw_start).strftime("%-I:%M %p")
    except (ValueError, TypeError):
        pass
    attendees = []
    for chunk in (e.get("attendees") or "").split(","):
        addr = chunk.strip().split(" ")[0].strip()
        if "@" in addr:
            attendees.append(addr)
    return {
        "start": when,
        "iso": raw_start,
        "summary": e.get("summary", ""),
        "location": e.get("location", ""),
        "attendees": attendees,
        "join": e.get("zoom_link") or e.get("meet_link") or "",
    }


_BLOCK_WORDS = (
    "do not book", "no meeting", "shuttle", "break", "lunch", "prep for the day",
    "focus time", "focus block", "hold", "ooo", "out of office", "commute",
    "busy", "blocked", "wfh", "gym", "personal", "dnd",
)


def is_meeting(e: dict) -> bool:
    """Heuristic: a real meeting vs a calendar hold/block (Do Not Book, Break…)."""
    name = (e.get("summary") or "").lower().strip()
    if not name:
        return False
    return not any(w in name for w in _BLOCK_WORDS)


def _events_on(target: date, limit: int) -> list[dict]:
    """All events on `target` (full day, incl. earlier ones).

    The CLI accepts --since/--until only as full RFC3339 timestamps (bare dates
    400), so build local-midnight bounds. Falls back to listing upcoming events
    and filtering by date if the ranged query is rejected.
    """
    since = datetime.combine(target, time.min).astimezone().isoformat()
    until = datetime.combine(target + timedelta(days=1), time.min).astimezone().isoformat()
    try:
        rows = _run_json(["google.calendar.event", "list",
                          f"--since={since}", f"--until={until}", f"--limit={limit}"])
    except MetaCLIError:
        rows = [e for e in _run_json(["google.calendar.event", "list", f"--limit={max(limit*3, 30)}"])
                if (e.get("start", "")[:10] == target.isoformat())]
    return [_normalize_event(e) for e in rows][:limit]


def calendar_today(limit: int = 20) -> list[dict]:
    """Today's calendar events (normalized: start, summary, location, attendees…)."""
    return _events_on(date.today(), limit)


def calendar_tomorrow(limit: int = 20) -> list[dict]:
    return _events_on(date.today() + timedelta(days=1), limit)


def gmail_unread(limit: int = 25) -> list[dict]:
    """Unread inbox messages (id, from, subject, snippet, date)."""
    return _run_json(
        ["google.gmail.message", "list", "--query=is:unread in:inbox", f"--limit={limit}"]
    ) or []


def gmail_awaiting(limit: int = 25) -> list[dict]:
    """Threads Jo sent that have had no reply in a few days (waiting-on)."""
    return _run_json(
        ["google.gmail.message", "list",
         "--query=in:sent newer_than:14d older_than:2d", f"--limit={limit}"]
    ) or []


def gmail_search(query: str, limit: int = 5) -> list[dict]:
    """Generic Gmail search (full Gmail query syntax)."""
    return _run_json(["google.gmail.message", "list", f"--query={query}", f"--limit={limit}"]) or []


def directory_lookup(email: str) -> dict:
    """Best-effort org lookup for an attendee (name, title, manager).

    Returns {} if the directory isn't reachable — callers degrade gracefully.
    """
    try:
        rows = _run_json(["google.people.directory", "search", f"--query={email}", "--limit=1"])
        if isinstance(rows, list) and rows:
            return rows[0]
        if isinstance(rows, dict):
            return rows
    except MetaCLIError:
        pass
    return {}


def drive_recent_docs(limit: int = 15) -> list[dict]:
    """Recently modified/shared docs (default columns include name, owner, url)."""
    return _run_json(["google.drive.file", "list", f"--limit={limit}"]) or []


# ── Outbound (DRAFTS ONLY) ─────────────────────────────────────────────────

def gmail_draft_reply(reply_to_id: str, body: str, dry_run: bool = False) -> dict:
    """Create a Gmail DRAFT reply to a message (To/Subject inferred). Never sends."""
    args = ["google.gmail.draft", "create", f"--reply-to={reply_to_id}", f"--body={body}"]
    if dry_run:
        args.append("--dry-run")
    out = _run(args, timeout=60)
    return {"ok": True, "raw": out.strip()[:500]}


def gmail_draft_new(to: str, subject: str, body: str, dry_run: bool = False) -> dict:
    """Create a brand-new Gmail DRAFT (e.g. a nudge). Never sends."""
    args = ["google.gmail.draft", "create", f"--to={to}", f"--subject={subject}", f"--body={body}"]
    if dry_run:
        args.append("--dry-run")
    out = _run(args, timeout=60)
    return {"ok": True, "raw": out.strip()[:500]}


def gdoc_create_draft(title: str, markdown_body: str) -> dict:
    """Stage a Google Doc (used for the Top of Mind draft). Private by default."""
    out = _run(["google.docs", "create", f"--title={title}", f"--content={markdown_body}"], timeout=90)
    # Surface a URL if the CLI printed one.
    url = ""
    for tok in out.split():
        if "docs.google.com/document" in tok:
            url = tok.strip().strip(".,")
            break
    return {"ok": True, "url": url, "raw": out.strip()[:500]}


def gdoc_text(url: str) -> str:
    """Fetch a Google Doc's plain text (for A10 doc→actions). '' on failure."""
    try:
        return _run(["google.docs", "get", f"--url={url}", "--format=text"], timeout=90)
    except MetaCLIError:
        return ""


# ── Workplace (best-effort) ─────────────────────────────────────────────────
# There is no clean first-party "my Workplace feed / notifications" CLI yet, so
# these are intentionally thin: they raise NotAuthenticated so jobs fall back to
# sample fixtures. Wire them to the real Workplace/Graph surface when available.

def workplace_key_updates(limit: int = 10) -> list[dict]:
    """Recent leadership/team key updates. TODO: wire to the Workplace surface."""
    raise NotAuthenticated("Workplace connector not wired yet — using sample data.")


def workplace_top_posts(limit: int = 10) -> list[dict]:
    """Top posts across Jo's groups. TODO: wire to the Workplace surface."""
    raise NotAuthenticated("Workplace connector not wired yet — using sample data.")


def workplace_notifications(limit: int = 25) -> list[dict]:
    """Workplace notifications to triage. TODO: wire to the Workplace surface."""
    raise NotAuthenticated("Workplace connector not wired yet — using sample data.")
