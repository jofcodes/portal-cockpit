"""Local Llama text helper.

Talks to Ollama's OpenAI-compatible endpoint on 127.0.0.1 (Meta-approved Llama
models only, fully local). Mirrors the call pattern in
beehive_monitor/level2.py but for text-only summarization/drafting.
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from .config import CONFIG

log = logging.getLogger("cockpit.llm")

_client: OpenAI | None = None
_resolved_model: str | None = None


def _list_installed_models() -> list[str]:
    """Best-effort: ask Ollama which models are installed."""
    try:
        import urllib.request

        host = CONFIG.llm.host.rsplit("/v1", 1)[0]
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as r:
            data = json.load(r)
        return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


def _pick_model() -> str:
    """Resolve a usable model: configured one if present, else first fallback."""
    global _resolved_model
    if _resolved_model:
        return _resolved_model
    installed = _list_installed_models()
    if CONFIG.llm.model in installed:
        _resolved_model = CONFIG.llm.model
    else:
        _resolved_model = next(
            (m for m in CONFIG.llm.fallback_models if m in installed),
            CONFIG.llm.model,  # last resort: try the configured name anyway
        )
        if _resolved_model != CONFIG.llm.model:
            log.warning("Model %s not installed; using %s", CONFIG.llm.model, _resolved_model)
    return _resolved_model


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=CONFIG.llm.host, api_key=CONFIG.llm.api_key)
    return _client


def available() -> bool:
    """True if Ollama is reachable and has at least one usable model."""
    return bool(_list_installed_models())


def chat(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    """Single-turn completion. Returns the model's text (empty string on error)."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = _get_client().chat.completions.create(
            model=_pick_model(),
            messages=messages,
            max_tokens=max_tokens or CONFIG.llm.max_tokens,
            temperature=CONFIG.llm.temperature,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 — never let the LLM break a job
        log.error("LLM call failed: %s", exc)
        return ""


def chat_json(prompt: str, system: str | None = None, max_tokens: int | None = None) -> dict:
    """Completion that should return a JSON object; parses defensively.

    Returns {} if nothing parseable comes back, so callers can fall back.
    """
    sys_prompt = (system or "") + "\nRespond with ONLY a single JSON object, no prose, no code fences."
    text = chat(prompt, system=sys_prompt.strip(), max_tokens=max_tokens)
    if not text:
        return {}
    # Strip code fences if the model added them.
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {}
