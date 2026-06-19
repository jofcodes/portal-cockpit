"""Cockpit configuration — paths, model, and guardrail settings.

Everything is local. The LLM points at Ollama on 127.0.0.1; outbound actions are
draft-only by policy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────
# cockpit/ lives at <repo>/cockpit, so the repo root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
PORTAL_DATA_DIR = PROJECT_DIR / "portal_data"
COCKPIT_APP_DIR = PROJECT_DIR / "cockpit_app"
DASHBOARD_ASSET = COCKPIT_APP_DIR / "app" / "src" / "main" / "assets" / "dashboard" / "index.html"
DASHBOARD_PREVIEW = PORTAL_DATA_DIR / "cockpit.html"
LOGS_DIR = PROJECT_DIR / "logs"

# ADB path (same location the bee monitor uses).
ADB = os.environ.get("ADB", "/usr/local/platform-tools/adb")
# Where the Cockpit app reads a pushed "quick refresh" dashboard from.
PORTAL_PKG = "com.josephine.cockpit"
PORTAL_PUSH_PATH = f"/sdcard/Android/data/{PORTAL_PKG}/files/dashboard/index.html"


@dataclass
class LLMConfig:
    """Local Llama via Ollama's OpenAI-compatible endpoint (127.0.0.1 only)."""

    host: str = "http://127.0.0.1:11434/v1"
    # Preferred text model; falls back to whatever is installed (see llm.py).
    model: str = os.environ.get("COCKPIT_MODEL", "llama3.1:8b")
    fallback_models: tuple[str, ...] = ("llama3.1:8b", "llama3:8b", "llava:7b")
    api_key: str = "ollama"  # Ollama ignores the key but the client requires one.
    max_tokens: int = 600
    temperature: float = 0.4


@dataclass
class UserConfig:
    name: str = "Jo"
    email: str = os.environ.get("COCKPIT_EMAIL", "j0sephine@meta.com")
    timezone: str = os.environ.get("COCKPIT_TZ", "America/Los_Angeles")
    # Top of Mind: which Workplace group Jo posts to + a few example posts.
    # Filled in at the Top-of-Mind build step.
    top_of_mind_group: str = os.environ.get("COCKPIT_TOM_GROUP", "")


@dataclass
class Guardrails:
    """Drafts, never sends. Read-only digests may run unattended."""

    drafts_only: bool = True
    # If True and connectors aren't authenticated, jobs use sample fixtures so
    # the dashboard/app can be built and demoed before `jf auth`.
    fall_back_to_sample: bool = True


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    user: UserConfig = field(default_factory=UserConfig)
    guardrails: Guardrails = field(default_factory=Guardrails)


CONFIG = Config()
