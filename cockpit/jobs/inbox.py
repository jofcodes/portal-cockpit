"""A2 — Inbox triage + draft replies, and A5 — Follow-up / waiting-on tracker.

Prioritizes unread mail and stages Gmail DRAFT replies for the items that need
one (never sends). Surfaces threads Jo is waiting on and stages draft nudges.

    python -m cockpit.jobs.inbox            # create drafts
    python -m cockpit.jobs.inbox --dry-run  # don't create drafts, just plan
"""

from __future__ import annotations

import argparse
import logging

from .. import connectors, llm
from ..config import CONFIG
from . import write_data

log = logging.getLogger("cockpit.jobs.inbox")


def _gather() -> tuple[list[dict], list[dict], bool]:
    if connectors.is_authenticated():
        try:
            return connectors.gmail_unread(limit=25), connectors.gmail_awaiting(limit=25), False
        except connectors.MetaCLIError as exc:
            log.warning("Connector error, falling back to sample: %s", exc)
    if not CONFIG.guardrails.fall_back_to_sample:
        raise RuntimeError("Connectors unauthenticated and sample fallback disabled.")
    from .. import sample_data as s
    return s.SAMPLE_UNREAD, s.SAMPLE_AWAITING, True


def _triage(unread: list[dict]) -> list[dict]:
    """Ask the model to rank unread mail and flag which need a reply."""
    listing = "\n".join(
        f"{i}. from {m.get('from','')} | {m.get('subject','')} | {m.get('snippet','')[:120]}"
        for i, m in enumerate(unread)
    )
    prompt = (
        f"Triage {CONFIG.user.name}'s unread email. For each, give priority "
        f"(high/medium/low) and whether it needs a reply.\n\n{listing}\n\n"
        f'Return JSON: {{"items": [{{"index": int, "priority": str, '
        f'"needs_reply": bool, "reason": str}}]}}'
    )
    ranked = llm.chat_json(prompt).get("items", []) if llm.available() else []
    by_index = {r.get("index"): r for r in ranked if isinstance(r, dict)}
    out = []
    for i, m in enumerate(unread):
        r = by_index.get(i, {})
        out.append({
            **m,
            "priority": r.get("priority", "medium"),
            "needs_reply": bool(r.get("needs_reply", False)),
            "reason": r.get("reason", ""),
        })
    rank = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda x: rank.get(x["priority"], 1))
    return out


def _draft_reply_body(msg: dict) -> str:
    prompt = (
        f"Draft a brief, friendly reply from {CONFIG.user.name} to this email. "
        f"Keep it 2-4 sentences, match a warm professional tone, no signature.\n\n"
        f"From: {msg.get('from','')}\nSubject: {msg.get('subject','')}\n"
        f"Body/snippet: {msg.get('snippet','')}"
    )
    return llm.chat(prompt) or "Thanks for this — taking a look and will follow up shortly."


def build(dry_run: bool = False) -> dict:
    unread, awaiting, used_sample = _gather()
    triaged = _triage(unread)

    drafted = []
    # Stage replies only for the items that need one (cap to avoid spamming drafts).
    to_draft = [m for m in triaged if m["needs_reply"]][:5]
    for m in to_draft:
        body = _draft_reply_body(m)
        entry = {"subject": m.get("subject", ""), "to": m.get("from", ""),
                 "preview": body[:200], "msg_id": m.get("id", "")}
        if not used_sample and CONFIG.guardrails.drafts_only:
            try:
                connectors.gmail_draft_reply(m["id"], body, dry_run=dry_run)
                entry["draft_created"] = not dry_run
            except connectors.MetaCLIError as exc:
                log.warning("Could not create draft: %s", exc)
                entry["draft_created"] = False
        else:
            entry["draft_created"] = False  # sample mode: previews only
        drafted.append(entry)

    # A5: nudges for waiting-on threads (draft, never send).
    nudges = []
    for t in awaiting[:5]:
        body = (llm.chat(
            f"Write a one-line friendly nudge from {CONFIG.user.name} following up on: "
            f"'{t.get('subject','')}' (last note: {t.get('snippet','')}).")
            or f"Hi — gently following up on '{t.get('subject','')}'. Thanks!")
        nudges.append({"to": t.get("to", ""), "subject": t.get("subject", ""),
                       "preview": body[:200], "sent_ago": t.get("sent", "")})

    payload = {
        "authenticated": not used_sample,
        "sample": used_sample,
        "unread_count": len(unread),
        "drafted_count": sum(1 for d in drafted if d.get("draft_created")),
        "priority": triaged[:8],
        "drafts": drafted,
        "awaiting": awaiting,
        "nudges": nudges,
    }
    write_data("inbox", payload)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Plan drafts without creating them")
    args = ap.parse_args()
    p = build(dry_run=args.dry_run)
    print(f"Inbox: {p['unread_count']} unread, {len(p['drafts'])} replies staged, "
          f"{len(p['nudges'])} nudges. (sample: {p['sample']})")


if __name__ == "__main__":
    main()
