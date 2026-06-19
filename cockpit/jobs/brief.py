"""A1 — Morning briefing.

Daily 8am digest: today's agenda, priority email, and overnight-shared docs,
summarized into a glanceable headline by the local Llama model. Read-only —
runs unattended.

    python -m cockpit.jobs.brief
"""

from __future__ import annotations

import logging

from .. import connectors, llm
from ..config import CONFIG
from . import write_data

log = logging.getLogger("cockpit.jobs.brief")


def _gather() -> tuple[dict, bool]:
    """Return (raw signals, used_sample)."""
    if connectors.is_authenticated():
        try:
            return {
                "agenda": connectors.calendar_today(),
                "mail": connectors.gmail_unread(limit=15),
                "docs": connectors.drive_recent_docs(limit=10),
            }, False
        except connectors.MetaCLIError as exc:
            log.warning("Connector error, falling back to sample: %s", exc)
    if not CONFIG.guardrails.fall_back_to_sample:
        raise RuntimeError("Connectors unauthenticated and sample fallback disabled.")
    from .. import sample_data as s
    return {"agenda": s.SAMPLE_CALENDAR, "mail": s.SAMPLE_UNREAD, "docs": s.SAMPLE_DOCS}, True


def _summarize(raw: dict) -> dict:
    """Use the local model to produce a short headline + per-item one-liners."""
    agenda_lines = "\n".join(f"- {e.get('start','')}: {e.get('summary','')}" for e in raw["agenda"])
    mail_lines = "\n".join(f"- {m.get('from','')}: {m.get('subject','')}" for m in raw["mail"][:8])
    doc_lines = "\n".join(f"- {d.get('name','')}" for d in raw["docs"][:6])
    prompt = (
        f"You are {CONFIG.user.name}'s executive assistant. Write a 1-2 sentence "
        f"morning headline (warm, concise, no greeting) capturing the most important "
        f"thing about today, then 3 short bullet 'focus' items.\n\n"
        f"AGENDA:\n{agenda_lines or '(none)'}\n\n"
        f"UNREAD MAIL:\n{mail_lines or '(none)'}\n\n"
        f"DOCS SHARED:\n{doc_lines or '(none)'}\n\n"
        f"Return JSON: {{\"headline\": str, \"focus\": [str, str, str]}}"
    )
    out = llm.chat_json(prompt) if llm.available() else {}
    return {
        "headline": out.get("headline") or _fallback_headline(raw),
        "focus": out.get("focus") or _fallback_focus(raw),
    }


def _fallback_headline(raw: dict) -> str:
    n_mtg, n_mail = len(raw["agenda"]), len(raw["mail"])
    first = raw["agenda"][0]["summary"] if raw["agenda"] else "no meetings"
    return f"{n_mtg} meetings today (first: {first}), {n_mail} unread to triage."


def _fallback_focus(raw: dict) -> list[str]:
    items = []
    if raw["agenda"]:
        items.append(f"Prep for {raw['agenda'][0].get('summary','first meeting')}")
    if raw["mail"]:
        items.append(f"Triage {len(raw['mail'])} unread emails")
    if raw["docs"]:
        items.append(f"Review {raw['docs'][0].get('name','a shared doc')}")
    return items or ["Clear inbox", "Plan the day", "Deep work block"]


def _next_up(events: list[dict]) -> dict | None:
    """The next event starting now-or-later; else the day's first event."""
    from datetime import datetime
    now = datetime.now().astimezone()
    for e in events:
        try:
            if datetime.fromisoformat(e.get("iso", "")) >= now:
                return e
        except (ValueError, TypeError):
            continue
    return events[0] if events else None


def build() -> dict:
    raw, used_sample = _gather()
    # Drop calendar holds/blocks (Do Not Book, Break, Shuttle…) from the agenda.
    raw["agenda"] = [e for e in raw["agenda"] if connectors.is_meeting(e)]
    summary = _summarize(raw)
    next_meeting = _next_up(raw["agenda"])
    payload = {
        "authenticated": not used_sample,
        "sample": used_sample,
        "headline": summary["headline"],
        "focus": summary["focus"],
        "next_meeting": next_meeting,
        "agenda": raw["agenda"],
        "priority_mail": raw["mail"][:6],
        "docs": raw["docs"][:6],
    }
    return write_data("brief", payload) and payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    p = build()
    print(f"Morning brief: {p['headline']}")
    print(f"(sample data: {p['sample']})")


if __name__ == "__main__":
    main()
