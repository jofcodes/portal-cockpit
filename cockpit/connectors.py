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


def _run_json(args: list[str], timeout: int = 60):
    """Run a meta command with --output=json and parse the result."""
    out = _run([*args, "--output=json"], timeout=timeout)
    out = out.strip()
    if not out:
        return []
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Some commands print a preamble line before the JSON body.
        start = out.find("[")
        brace = out.find("{")
        if start < 0 or (0 <= brace < start):
            start = brace
        if start >= 0:
            try:
                return json.loads(out[start:])
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

def calendar_today(limit: int = 20) -> list[dict]:
    """Today's calendar events (start, summary, location, attendees…)."""
    return _run_json(
        ["google.calendar.event", "list", "--since=today", "--until=tomorrow", f"--limit={limit}"]
    ) or []


def calendar_tomorrow(limit: int = 20) -> list[dict]:
    return _run_json(
        ["google.calendar.event", "list", "--since=tomorrow", "--until=in 2 days", f"--limit={limit}"]
    ) or []


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
    """Recently modified/shared docs (overnight-shared etc.)."""
    return _run_json(
        ["google.drive.file", "list", f"--limit={limit}",
         "--columns=name,type,owner,modifiedTime,webViewLink"]
    ) or []


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
