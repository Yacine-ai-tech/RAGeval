"""Self-contained settings + logging for the installable ``rageval`` package.

The published package (``pip install omnismart-rageval``) must work on any machine, so it cannot
import the RAGeval *application's* ``core`` module (which isn't shipped in the wheel). This mirrors
exactly the settings the package needs, reading the **same environment variables**, so behaviour is
identical whether ``rageval`` is imported standalone or from within the app repo.

IMPORTANT: When changing a default value here, mirror it in core/config.py and vice versa.
The two modules must stay in sync — there is no runtime enforcement.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

RAGEVAL_HOME = Path(os.getenv("RAGEVAL_HOME", str(Path.home() / ".rageval")))
try:
    RAGEVAL_HOME.mkdir(parents=True, exist_ok=True)
except Exception:  # pragma: no cover - read-only home, etc.
    pass


# Canonical default judge list — must match core/config.py exactly.
# gemini/gemini-flash-latest is the current production alias.
_DEFAULT_JUDGE_MODELS = (
    "anthropic/claude-haiku-4-5,"
    "groq/llama-3.3-70b-versatile,"
    "gemini/gemini-flash-latest,"
    "openai/gpt-4o-mini"
)


class _Settings:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    RAGEVAL_STORE = os.getenv("RAGEVAL_STORE", "postgres")
    RAGEVAL_DB_PATH = os.getenv("RAGEVAL_DB_PATH", str(RAGEVAL_HOME / "rageval.db"))
    # RAGEVAL_POSTGRES_URL only — deliberately no fallback to a bare POSTGRES_URL here.
    # This matters most in the installable-package settings: a fallback would make
    # `rageval` silently adopt a host app's own, unrelated database whenever it's
    # imported into a host that (reasonably) also uses the generic POSTGRES_URL name for
    # itself — confirmed live: this exact fallback wrote rageval's schema into
    # AgentKit's real production Postgres before being removed. The standalone RAGeval
    # app (api.py) does its own one-time POSTGRES_URL->RAGEVAL_POSTGRES_URL compat shim
    # at startup, scoped to just that process — this library-settings module never does.
    POSTGRES_URL = os.getenv("RAGEVAL_POSTGRES_URL", "")
    RAGEVAL_OTEL_ENDPOINT = os.getenv("RAGEVAL_OTEL_ENDPOINT", "")
    RAGEVAL_EMBEDDING_DIM = int(os.getenv("RAGEVAL_EMBEDDING_DIM", "1024"))

    LLM_DEFAULT = os.getenv("LLM_DEFAULT", "groq/llama-3.3-70b-versatile")
    LLM_JUDGE = os.getenv("LLM_JUDGE", "anthropic/claude-haiku-4-5")
    JUDGE_MODELS = [
        m.strip() for m in os.getenv(
            "JUDGE_MODELS", _DEFAULT_JUDGE_MODELS,
        ).split(",") if m.strip()
    ]
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    # NOTE: GEMINI_API_KEY below is a snapshot captured at import time.
    # The Gemini judge reads os.environ["GEMINI_API_KEY"] directly at call time
    # (via google.genai.Client), so it always sees the current value.
    # This snapshot is kept for diagnostic inspection only — do NOT gate judge
    # calls on this field; gate on os.getenv("GEMINI_API_KEY") instead.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


settings = _Settings()

_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a stdout logger, configuring the root handler once (idempotent)."""
    global _configured
    if not _configured:
        root = logging.getLogger()
        root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        if not root.handlers:
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(logging.Formatter(settings.LOG_FORMAT))
            root.addHandler(sh)
        _configured = True
    return logging.getLogger(name or "rageval")
