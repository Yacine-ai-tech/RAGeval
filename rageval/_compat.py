"""Self-contained settings + logging for the installable ``rageval`` package.

The published package (``pip install omnismart-rageval``) must work on any machine, so it cannot
import the RAGeval *application's* ``core`` module (which isn't shipped in the wheel). This mirrors
exactly the settings the package needs, reading the **same environment variables**, so behaviour is
identical whether ``rageval`` is imported standalone or from within the app repo.
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


class _Settings:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    RAGEVAL_STORE = os.getenv("RAGEVAL_STORE", "sqlite")
    RAGEVAL_DB_PATH = os.getenv("RAGEVAL_DB_PATH", str(RAGEVAL_HOME / "rageval.db"))
    POSTGRES_URL = os.getenv("POSTGRES_URL", "")
    RAGEVAL_OTEL_ENDPOINT = os.getenv("RAGEVAL_OTEL_ENDPOINT", "")

    LLM_DEFAULT = os.getenv("LLM_DEFAULT", "groq/llama-3.3-70b-versatile")
    LLM_JUDGE = os.getenv("LLM_JUDGE", "anthropic/claude-haiku-4-5")
    JUDGE_MODELS = [
        m.strip() for m in os.getenv(
            "JUDGE_MODELS",
            "anthropic/claude-haiku-4-5,groq/llama-3.3-70b-versatile,gemini/gemini-1.5-flash",
        ).split(",") if m.strip()
    ]
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
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
