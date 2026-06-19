"""Portal Productivity Cockpit.

A glanceable productivity hub for Meta Portal, built on the same pattern as the
beehive monitor in this repo: local Python jobs gather signals from Jo's work
tools, a local Llama model summarizes/drafts, results are written as JSON, and a
self-contained dashboard renders them on the Portal.

Layers:
  connectors.py  — read Gmail / Calendar / Drive (and stage Workplace drafts)
                   via the `meta google.*` CLI.
  llm.py         — local Llama text helper (Ollama, bound to 127.0.0.1).
  jobs/          — one module per automation (brief, inbox, wrap, top_of_mind),
                   each writes portal_data/<name>.json.
  build_cockpit.py — render portal_data/*.json into one self-contained HTML page.
  server.py      — Flask "brain": serve the dashboard + trigger refreshes.

Guardrails: anything outbound (email replies, posts) is always staged as a
DRAFT for one-tap approval — never auto-sent. The LLM is local-only.
"""
