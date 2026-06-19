"""A6 — Weekly Workplace digest.

Friday summary of team/leadership key updates + top posts, condensed by the
local Llama model. Read-only; runs unattended (Fri PM).

    python -m cockpit.jobs.workplace_digest

NOTE: the Workplace connector isn't wired yet (no clean first-party CLI), so
this currently runs on sample data. When `connectors.workplace_*` are wired,
it switches to real data automatically.
"""

from __future__ import annotations

import logging

from .. import connectors, llm
from ..config import CONFIG
from . import write_data

log = logging.getLogger("cockpit.jobs.workplace_digest")


def _gather() -> tuple[list[dict], list[dict], bool]:
    try:
        return (connectors.workplace_key_updates(limit=8),
                connectors.workplace_top_posts(limit=5), False)
    except connectors.MetaCLIError as exc:
        log.info("%s", exc)
    from .. import sample_data as s
    return s.SAMPLE_KEY_UPDATES, s.SAMPLE_TOP_POSTS, True


def _summary(updates: list[dict], posts: list[dict]) -> str:
    upd = "\n".join(f"- {u.get('author','')}: {u.get('title','')} — {u.get('summary','')}" for u in updates)
    pos = "\n".join(f"- {p.get('title','')} ({p.get('group','')})" for p in posts)
    prompt = (
        f"Write a tight 2-3 sentence Friday digest for {CONFIG.user.name} of this week's "
        f"key Workplace updates and notable posts. Lead with what matters most. No greeting.\n\n"
        f"KEY UPDATES:\n{upd or '(none)'}\n\nTOP POSTS:\n{pos or '(none)'}"
    )
    return (llm.chat(prompt) if llm.available() else "") or (
        f"{len(updates)} key updates and {len(posts)} notable posts this week — "
        f"highlights from leadership on Portal/local-first AI."
    )


def build() -> dict:
    updates, posts, used_sample = _gather()
    payload = {
        "authenticated": not used_sample,
        "sample": used_sample,
        "summary": _summary(updates, posts),
        "key_updates": updates,
        "top_posts": posts,
    }
    write_data("digest", payload)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    p = build()
    print("Weekly Workplace digest:\n" + p["summary"] + f"\n(sample: {p['sample']})")


if __name__ == "__main__":
    main()
