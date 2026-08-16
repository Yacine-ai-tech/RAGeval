"""Slim RAGeval configuration — env-driven.

IMPORTANT: _DEFAULT_JUDGE_MODELS below must stay in sync with the constant of
the same name in src/rageval/_compat.py. There is no runtime enforcement between
the two settings modules (one is the app config, the other is the pip-package
compat shim) — a single-source-of-truth refactor is tracked in the backlog.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
RAGEVAL_HOME = Path(os.getenv("RAGEVAL_HOME", str(Path.home() / ".rageval")))
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RAGEVAL_HOME.mkdir(parents=True, exist_ok=True)

# Canonical default — must mirror _compat.py exactly.
_DEFAULT_JUDGE_MODELS = (
    "anthropic/claude-haiku-4-5,"
    "groq/llama-3.3-70b-versatile,"
    "gemini/gemini-flash-latest,"
    "openai/gpt-4o-mini"
)


class Settings:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    LOGS_DIR = str(LOGS_DIR)

    # CORS: comma-separated allowed origins. Empty -> "*" (dev). Set in production.
    CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",") if o.strip()]

    RAGEVAL_STORE = os.getenv("RAGEVAL_STORE", "sqlite")
    RAGEVAL_DB_PATH = os.getenv("RAGEVAL_DB_PATH", str(RAGEVAL_HOME / "rageval.db"))
    # RAGEVAL_POSTGRES_URL only — deliberately no fallback to a bare POSTGRES_URL here.
    # A fallback would make rageval silently adopt a host app's own, unrelated database
    # whenever rageval is embedded as a library and that host (reasonably) also uses the
    # generic POSTGRES_URL name for itself. The standalone app (api.py) does its own
    # one-time POSTGRES_URL->RAGEVAL_POSTGRES_URL compat shim at startup, scoped to just
    # that process — see api.py.
    POSTGRES_URL = os.getenv("RAGEVAL_POSTGRES_URL", "")
    RAGEVAL_OTEL_ENDPOINT = os.getenv("RAGEVAL_OTEL_ENDPOINT", "")
    # Vector column width for the Postgres/pgvector production tier. Must match the
    # output dimension of EMBEDDING_MODEL below (1024 fits bge-large/bge-m3/arctic-embed-l;
    # override if you configure a different-dimension embedding model).
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
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


settings = Settings()
