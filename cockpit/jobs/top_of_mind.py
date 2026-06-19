"""Monday "Top of Mind".

Learns Jo's voice from a few past posts, gathers the week's signals, and drafts a
Top of Mind post in her voice. The draft is STAGED (written to portal_data and,
when authenticated, to a private Google Doc) for one-tap approval — never posted.

    python -m cockpit.jobs.top_of_mind

Needs from Jo (to go live): which Workplace group she posts to, and 2-3 real
example posts. Set COCKPIT_TOM_GROUP and drop examples in voice_examples.txt,
or pass them in; until then sample examples are used.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .. import connectors, llm
from ..config import CONFIG, PROJECT_DIR
from . import write_data

log = logging.getLogger("cockpit.jobs.top_of_mind")

VOICE_FILE = PROJECT_DIR / "cockpit" / "voice_examples.txt"


def _examples() -> list[str]:
    """Real examples from voice_examples.txt if present, else samples."""
    if VOICE_FILE.exists():
        text = VOICE_FILE.read_text().strip()
        if text:
            # Posts separated by a line of '---'.
            return [p.strip() for p in text.split("\n---\n") if p.strip()]
    from .. import sample_data as s
    return s.SAMPLE_TOM_EXAMPLES


def _style_profile(examples: list[str]) -> str:
    joined = "\n\n=== EXAMPLE ===\n".join(examples)
    prompt = (
        "Analyze these past 'Top of Mind' posts and describe the author's voice in "
        "5 short bullet points (structure, tone, length, opening/closing habits, "
        "recurring sections). Be specific and reusable.\n\n" + joined
    )
    return llm.chat(prompt) if llm.available() else (
        "- Warm, first-person, concise\n- Numbered 'things on my mind' list\n"
        "- Short paragraphs\n- Closes with gratitude / 'more soon'\n- Occasional emoji"
    )


def _week_signals() -> dict:
    if connectors.is_authenticated():
        try:
            return {"meetings": connectors.calendar_today() + connectors.calendar_tomorrow(),
                    "docs": connectors.drive_recent_docs(limit=10)}
        except connectors.MetaCLIError as exc:
            log.warning("Connector error, using sample signals: %s", exc)
    from .. import sample_data as s
    return {"meetings": s.SAMPLE_CALENDAR, "docs": s.SAMPLE_DOCS}


def _draft_post(profile: str, signals: dict) -> str:
    mtg = "\n".join(f"- {m.get('summary','')}" for m in signals["meetings"][:8])
    docs = "\n".join(f"- {d.get('name','')}" for d in signals["docs"][:6])
    prompt = (
        f"Write a 'Top of Mind' post in {CONFIG.user.name}'s voice for this week. "
        f"Match this voice profile:\n{profile}\n\n"
        f"Base it on this week's work signals:\nMEETINGS:\n{mtg}\n\nDOCS:\n{docs}\n\n"
        f"Keep it under 180 words. Output only the post text."
    )
    return (llm.chat(prompt, max_tokens=400) if llm.available() else "") or (
        "Top of Mind — this week\n\nHeads-down on shipping the Portal productivity "
        "cockpit. Biggest lesson: clone the architecture you've already proven and "
        "widen from the smallest working slice. More soon."
    )


def build() -> dict:
    examples = _examples()
    profile = _style_profile(examples)
    signals = _week_signals()
    draft = _draft_post(profile, signals)

    doc_url = ""
    if connectors.is_authenticated() and CONFIG.guardrails.drafts_only:
        try:
            res = connectors.gdoc_create_draft(
                title="Top of Mind — draft (review before posting)",
                markdown_body=draft)
            doc_url = res.get("url", "")
        except connectors.MetaCLIError as exc:
            log.warning("Could not stage Google Doc: %s", exc)

    payload = {
        "authenticated": connectors.is_authenticated(),
        "sample": not VOICE_FILE.exists(),
        "group": CONFIG.user.top_of_mind_group or "(set COCKPIT_TOM_GROUP)",
        "voice_profile": profile,
        "draft": draft,
        "doc_url": doc_url,
        "status": "draft_ready",
    }
    write_data("workplace", payload)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    p = build()
    print("Top of Mind draft staged:\n")
    print(p["draft"])
    if p["doc_url"]:
        print("\nDoc:", p["doc_url"])


if __name__ == "__main__":
    main()
