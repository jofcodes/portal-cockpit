#!/usr/bin/env python3
"""Cockpit server — the Mac "brain".

Serves the Cockpit dashboard and the underlying JSON, and triggers refreshes
(run the jobs → rebuild the dashboard → optionally push to the Portal). The
Portal's browser points at http://<mac-lan-ip>:<port>/.

Endpoints:
  GET  /            → the dashboard HTML (always freshly rendered from portal_data)
  GET  /brief|/inbox|/workplace|/wrap → the raw JSON for each automation
  GET  /health      → liveness + data freshness
  POST /refresh     → run the data jobs + rebuild, in the background
  GET  /status      → refresh state

    python -m cockpit.server                 # 0.0.0.0:8899
    python -m cockpit.server --port 9000
"""

from __future__ import annotations

import json
import logging
import socket
import threading
from datetime import datetime

from flask import Flask, Response, jsonify

from . import build_cockpit
from .config import PORTAL_DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("cockpit.server")

app = Flask(__name__)

_refresh_lock = threading.Lock()
_status = {"running": False, "last_refresh": None, "last_result": None, "error": None}


def _run_refresh() -> None:
    global _status
    with _refresh_lock:
        if _status["running"]:
            return
        _status["running"] = True
        _status["error"] = None
    try:
        # Import here so a connector/LLM hiccup can't stop the server booting.
        from .jobs import brief, inbox, wrap
        log.info("Refresh: brief…"); brief.build()
        log.info("Refresh: inbox…"); inbox.build()
        log.info("Refresh: wrap…"); wrap.build()
        build_cockpit.build()
        _status["last_refresh"] = datetime.now().isoformat(timespec="seconds")
        _status["last_result"] = "success"
        log.info("Refresh complete.")
    except Exception as exc:  # noqa: BLE001
        log.error("Refresh failed: %s", exc)
        _status["error"] = str(exc)
        _status["last_result"] = "error"
    finally:
        _status["running"] = False


@app.route("/")
def dashboard() -> Response:
    # Render fresh each load so the Portal always shows the latest portal_data.
    return Response(build_cockpit.generate(), mimetype="text/html")


def _serve_json(name: str) -> Response:
    path = PORTAL_DATA_DIR / f"{name}.json"
    if path.exists():
        return Response(path.read_text(), mimetype="application/json")
    return jsonify({"error": f"{name}.json not generated yet"}), 404


@app.route("/brief")
def brief_json():        return _serve_json("brief")
@app.route("/inbox")
def inbox_json():        return _serve_json("inbox")
@app.route("/workplace")
def workplace_json():    return _serve_json("workplace")
@app.route("/wrap")
def wrap_json():         return _serve_json("wrap")


@app.route("/health")
def health() -> Response:
    files = {p.stem: datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
             for p in PORTAL_DATA_DIR.glob("*.json")}
    return jsonify({"ok": True, "data": files, **_status})


@app.route("/refresh", methods=["POST", "GET"])
def refresh() -> Response:
    if _status["running"]:
        return jsonify({"status": "already_running", **_status})
    threading.Thread(target=_run_refresh, daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/status")
def status() -> Response:
    return jsonify(_status)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]
    except Exception:
        ip = "localhost"
    finally:
        s.close()
    print(f"\n{'='*48}\n  Cockpit server\n  Dashboard: http://{ip}:{args.port}/\n"
          f"  Health:    http://{ip}:{args.port}/health\n{'='*48}\n")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
