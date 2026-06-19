"""A3 — Meeting-prep packets.

For the next meeting on today's calendar, assemble a quick prep packet:
attendees (with org/title when the directory is reachable), recent related email
threads, and a short LLM-written prep note. Read-only; runs unattended.

    python -m cockpit.jobs.meeting_prep
"""

from __future__ import annotations

import logging

from .. import connectors, llm
from ..config import CONFIG
from . import write_data

log = logging.getLogger("cockpit.jobs.meeting_prep")


def _next_meeting(events: list[dict]) -> dict | None:
    return events[0] if events else None


def _gather() -> tuple[dict | None, bool]:
    """Return (next_meeting_or_None, used_sample)."""
    if connectors.is_authenticated():
        try:
            return _next_meeting(connectors.calendar_today()), False
        except connectors.MetaCLIError as exc:
            log.warning("Connector error, using sample: %s", exc)
    from .. import sample_data as s
    return _next_meeting(s.SAMPLE_CALENDAR), True


def _attendees(meeting: dict, used_sample: bool) -> list[dict]:
    out = []
    for email in (meeting.get("attendees") or [])[:4]:
        info = {} if used_sample else connectors.directory_lookup(email)
        out.append({
            "email": email,
            "name": info.get("name") or info.get("displayName") or email.split("@")[0],
            "title": info.get("title") or info.get("jobTitle") or "",
            "manager": info.get("manager") or "",
        })
    return out


def _recent_threads(meeting: dict, attendees: list[dict], used_sample: bool) -> list[dict]:
    if used_sample:
        from .. import sample_data as s
        return s.SAMPLE_MEETING_THREADS
    threads: list[dict] = []
    # Threads mentioning the meeting subject, then recent mail from attendees.
    subj = meeting.get("summary", "")
    if subj:
        for m in connectors.gmail_search(f'subject:"{subj}" newer_than:30d', limit=3):
            threads.append({"subject": m.get("subject", ""), "from": m.get("from", "")})
    for a in attendees[:2]:
        for m in connectors.gmail_search(f'from:{a["email"]} newer_than:14d', limit=2):
            threads.append({"subject": m.get("subject", ""), "from": m.get("from", "")})
    # De-dupe by subject.
    seen, deduped = set(), []
    for t in threads:
        if t["subject"] and t["subject"] not in seen:
            seen.add(t["subject"]); deduped.append(t)
    return deduped[:5]


def _prep_note(meeting: dict, attendees: list[dict], threads: list[dict]) -> str:
    att = ", ".join(a["name"] + (f" ({a['title']})" if a["title"] else "") for a in attendees) or "—"
    thr = "\n".join(f"- {t['subject']}" for t in threads) or "(none found)"
    prompt = (
        f"In 2-3 sentences, prep {CONFIG.user.name} for this meeting: what it's likely about "
        f"and one thing to come ready with. No greeting.\n\n"
        f"Meeting: {meeting.get('summary','')} at {meeting.get('start','')}\n"
        f"Attendees: {att}\nRecent related threads:\n{thr}"
    )
    return (llm.chat(prompt) if llm.available() else "") or (
        f"Prep for {meeting.get('summary','this meeting')}: review the recent threads above "
        f"and come with a clear status + next step."
    )


def build() -> dict:
    meeting, used_sample = _gather()
    if not meeting:
        payload = {"authenticated": not used_sample, "sample": used_sample, "next_meeting": None}
        write_data("meetings", payload)
        return payload
    attendees = _attendees(meeting, used_sample)
    threads = _recent_threads(meeting, attendees, used_sample)
    payload = {
        "authenticated": not used_sample,
        "sample": used_sample,
        "next_meeting": meeting,
        "attendees": attendees,
        "threads": threads,
        "prep_note": _prep_note(meeting, attendees, threads),
    }
    write_data("meetings", payload)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    p = build()
    if p.get("next_meeting"):
        print(f"Meeting prep for: {p['next_meeting'].get('summary','')}")
        print(p.get("prep_note", ""))
    else:
        print("No upcoming meeting to prep.")


if __name__ == "__main__":
    main()
