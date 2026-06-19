"""A10 — Doc → action items.

Extracts decisions, owners, and action items from a Google Doc (or any text)
using the local Llama model. On-demand.

    python -m cockpit.jobs.doc_actions --url <google-doc-url>
    python -m cockpit.jobs.doc_actions            # sample doc text

Guardrail: read-only + extraction only. (Optionally posting a summary comment is
left to a human — never auto-posted.)
"""

from __future__ import annotations

import argparse
import logging

from .. import connectors, llm
from . import write_data

log = logging.getLogger("cockpit.jobs.doc_actions")


def _get_text(url: str | None) -> tuple[str, str, bool]:
    """Return (text, source_label, used_sample)."""
    if url:
        text = connectors.gdoc_text(url)
        if text.strip():
            return text, url, False
        log.warning("Could not read doc (auth?) — using sample text.")
    from .. import sample_data as s
    return s.SAMPLE_DOC_TEXT, "(sample doc)", True


def _extract(text: str) -> dict:
    prompt = (
        "Extract from this document: (1) decisions made, (2) action items with an owner "
        "and due date if stated, (3) open questions.\n\n"
        f"DOCUMENT:\n{text[:6000]}\n\n"
        'Return JSON: {"decisions": [str], "actions": [{"what": str, "owner": str, '
        '"due": str}], "open_questions": [str]}'
    )
    out = llm.chat_json(prompt, max_tokens=600) if llm.available() else {}
    return {
        "decisions": out.get("decisions", []),
        "actions": out.get("actions", []),
        "open_questions": out.get("open_questions", []),
    }


def build(url: str | None = None) -> dict:
    text, source, used_sample = _get_text(url)
    extracted = _extract(text)
    payload = {
        "authenticated": not used_sample,
        "sample": used_sample,
        "source": source,
        **extracted,
    }
    write_data("actions", payload)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="Google Doc URL to extract from")
    args = ap.parse_args()
    p = build(url=args.url)
    print(f"From {p['source']}: {len(p['actions'])} actions, {len(p['decisions'])} decisions, "
          f"{len(p['open_questions'])} open questions. (sample: {p['sample']})")


if __name__ == "__main__":
    main()
