"""Cockpit jobs — one module per automation.

Each job gathers signals (real connectors, or sample fixtures when not yet
authenticated), summarizes/drafts with the local Llama model, and writes
portal_data/<name>.json for the dashboard to render.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from ..config import PORTAL_DATA_DIR

log = logging.getLogger("cockpit.jobs")


def write_data(name: str, payload: dict) -> Path:
    """Write portal_data/<name>.json, stamping a generated timestamp."""
    PORTAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload.setdefault("generated", datetime.now().isoformat(timespec="seconds"))
    path = PORTAL_DATA_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2))
    log.info("Wrote %s (%d bytes)", path, path.stat().st_size)
    return path
