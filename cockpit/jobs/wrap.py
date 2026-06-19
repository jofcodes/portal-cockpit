"""A7 — End-of-day wrap.

5pm recap of the day + tomorrow's agenda pre-staged. Read-only; runs unattended.

    python -m cockpit.jobs.wrap
"""

from __future__ import annotations

import logging

from .. import connectors, llm
from ..config import CONFIG
from . import write_data

log = logging.getLogger("cockpit.jobs.wrap")


def _gather() -> tuple[dict, bool]:
    if connectors.is_authenticated():
        try:
            return {
                "today": connectors.calendar_today(),
                "tomorrow": connectors.calendar_tomorrow(),
                "unread": connectors.gmail_unread(limit=25),
            }, False
        except connectors.MetaCLIError as exc:
            log.warning("Connector error, falling back to sample: %s", exc)
    if not CONFIG.guardrails.fall_back_to_sample:
        raise RuntimeError("Connectors unauthenticated and sample fallback disabled.")
    from .. import sample_data as s
    return {"today": s.SAMPLE_CALENDAR, "tomorrow": s.SAMPLE_TOMORROW, "unread": s.SAMPLE_UNREAD}, True


def _recap(raw: dict) -> str:
    today = "\n".join(f"- {e.get('start','')}: {e.get('summary','')}" for e in raw["today"])
    prompt = (
        f"Write a warm 1-2 sentence end-of-day recap for {CONFIG.user.name} based on today's "
        f"meetings, and note what tomorrow's first item is. No greeting.\n\n"
        f"TODAY:\n{today or '(none)'}\n\n"
        f"TOMORROW FIRST: {raw['tomorrow'][0].get('summary','(nothing scheduled)') if raw['tomorrow'] else '(nothing scheduled)'}\n"
        f"UNREAD LEFT: {len(raw['unread'])}"
    )
    return (llm.chat(prompt) if llm.available() else "") or (
        f"{len(raw['today'])} meetings done; {len(raw['unread'])} unread remain. "
        f"Tomorrow starts with {raw['tomorrow'][0]['summary'] if raw['tomorrow'] else 'an open morning'}."
    )


def build() -> dict:
    raw, used_sample = _gather()
    payload = {
        "authenticated": not used_sample,
        "sample": used_sample,
        "recap": _recap(raw),
        "meetings_today": len(raw["today"]),
        "unread_remaining": len(raw["unread"]),
        "tomorrow": raw["tomorrow"],
    }
    write_data("wrap", payload)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    p = build()
    print(f"Wrap: {p['recap']} (sample: {p['sample']})")


if __name__ == "__main__":
    main()
