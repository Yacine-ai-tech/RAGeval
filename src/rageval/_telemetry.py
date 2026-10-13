"""Anonymous startup ping for library use (``@track`` and friends).

The API server (``rageval serve``) sends its own ping from ``api.py``. This covers the case where
RAGeval is used as a library only. Same rules: on by default, ``TELEMETRY_URL`` overrides the
destination (an empty value means the default), ``TELEMETRY_OPT_OUT=true`` or ``DO_NOT_TRACK=1``
disables it, at most one ping per 30 seconds per instance, no prompts or scores are ever sent.
"""
from __future__ import annotations

import os
import threading
import time
import uuid

DEFAULT_TELEMETRY_URL = "https://gateway.ysiddo-ai-projects.app/telemetry"
_started = False


def _dir() -> str:
    d = os.environ.get("RAGEVAL_HOME") or os.path.join(os.path.expanduser("~"), ".rageval")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _instance_id() -> str:
    path = os.path.join(_dir(), ".telemetry_instance_id")
    try:
        if os.path.exists(path):
            existing = open(path).read().strip()
            if existing:
                return existing
    except Exception:
        pass
    new_id = uuid.uuid4().hex[:16]
    try:
        with open(path, "w") as f:
            f.write(new_id)
    except Exception:
        pass
    return new_id



def _pyproject_version(pkg_name):
    import re
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        cand = os.path.join(here, "pyproject.toml")
        if os.path.exists(cand):
            m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', open(cand).read())
            if m:
                return m.group(1)
        here = os.path.dirname(here)
    return "unknown"


def _send() -> None:
    flag = os.environ.get("TELEMETRY_OPT_OUT", "").strip().lower()
    if flag in ("1", "true", "yes") or os.environ.get("DO_NOT_TRACK", "").strip() == "1":
        return
    url = (os.environ.get("TELEMETRY_URL") or DEFAULT_TELEMETRY_URL).strip()
    lock = os.path.join(_dir(), ".telemetry_last_ping")
    try:
        if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 30:
            return
        with open(lock, "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass
    try:
        from importlib.metadata import version

        ver = version("omnismart-rageval")
    except Exception:
        ver = _pyproject_version("omnismart-rageval")
    payload = {"service": "RAGeval", "event": "startup", "version": ver, "instance_id": _instance_id()}
    import requests

    for attempt in range(3):
        try:
            requests.post(url, json=payload, timeout=3)
            return
        except Exception:
            time.sleep(2 * (attempt + 1))


def send_startup_ping() -> None:
    global _started
    if _started or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    _started = True
    threading.Thread(target=_send, daemon=True).start()
