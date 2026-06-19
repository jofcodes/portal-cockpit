"""A8 — Notification triage.

Batches Workplace notifications and surfaces only the ones that need action,
filtering out FYI/reaction noise. Read-only; runs unattended (2×/day).

    python -m cockpit.jobs.notifications

NOTE: runs on sample data until connectors.workplace_notifications is wired.
"""

from __future__ import annotations

import logging

from .. import connectors, llm
from ..config import CONFIG
from . import write_data

log = logging.getLogger("cockpit.jobs.notifications")


def _gather() -> tuple[list[dict], bool]:
    try:
        return connectors.workplace_notifications(limit=30), False
    except connectors.MetaCLIError as exc:
        log.info("%s", exc)
    from .. import sample_data as s
    return s.SAMPLE_NOTIFICATIONS, True


def _classify(notifs: list[dict]) -> list[dict]:
    """Keep model-flagged action items; fall back to the 'action' hint field."""
    listing = "\n".join(
        f"{i}. [{n.get('kind','')}] from {n.get('from','')} re {n.get('context','')}: {n.get('text','')}"
        for i, n in enumerate(notifs)
    )
    prompt = (
        f"Which of these Workplace notifications need {CONFIG.user.name} to DO something "
        f"(reply, review, decide)? Ignore reactions/FYIs.\n\n{listing}\n\n"
        f'Return JSON: {{"action_indices": [int, ...]}}'
    )
    idx = set()
    if llm.available():
        idx = set(llm.chat_json(prompt).get("action_indices", []) or [])
    actions = []
    for i, n in enumerate(notifs):
        if i in idx or n.get("action"):
            actions.append(n)
    return actions


def build() -> dict:
    notifs, used_sample = _gather()
    actions = _classify(notifs)
    payload = {
        "authenticated": not used_sample,
        "sample": used_sample,
        "total": len(notifs),
        "action_count": len(actions),
        "actions": actions,
    }
    write_data("notifications", payload)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    p = build()
    print(f"Notifications: {p['action_count']}/{p['total']} need action. (sample: {p['sample']})")


if __name__ == "__main__":
    main()
