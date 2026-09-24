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

# Canonical default — must mirror _compat.py exactly. Each provider routes on its
# own standard API key (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY /
# GROQ_API_KEY) via litellm's normal "<provider>/<model>" prefix convention — set
# only the keys for the judges you want active; a missing key just skips that
# judge (MIN_JUDGES_REQUIRED handles the reduced quorum).
_DEFAULT_JUDGE_MODELS = (
    "anthropic/claude-haiku-4-5-20251001,"
    "openai/gpt-5-mini,"
    "gemini/gemini-3.6-flash,"
    "groq/openai/gpt-oss-120b"
)
# gemini-2.5-flash was retired by Google ("no longer available to new users" as of
# 2026-09-24, confirmed live: a 404 on every call) -- found while live-testing a new
# meta-judge arbiter, not by anyone noticing the production panel silently lost a
# judge. Since the panel degrades gracefully (MIN_JUDGES_REQUIRED), this had been
# failing quietly rather than loudly -- worth a real health check on judge models,
# not just a fix, as future work.


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

    LLM_DEFAULT = os.getenv("LLM_DEFAULT", "groq/openai/gpt-oss-120b")
    LLM_JUDGE = os.getenv("LLM_JUDGE", "anthropic/claude-haiku-4-5")

    JUDGE_MODELS = [
        m.strip() for m in os.getenv(
            "JUDGE_MODELS", _DEFAULT_JUDGE_MODELS,
        ).split(",") if m.strip()
    ]

    # Consensus aggregation strategy — see evaluator.py's score_groundedness_consensus()
    # docstring for the research this is grounded in. "weighted_mean" is the long-standing
    # default (kept for backward compatibility); "geometric_median" is the empirically and
    # theoretically more robust choice when judges may be correlated (RoPoLL, Acharya et
    # al. 2026) — for the scalar (single 0-1 score per judge) case here, the geometric
    # median reduces to the classical weighted median.
    RAGEVAL_AGGREGATION_STRATEGY = os.getenv("RAGEVAL_AGGREGATION_STRATEGY", "weighted_mean")
    # Adds a deterministic, non-LLM verification signal into the panel (numeric-fact
    # consistency + lexical/semantic overlap against the retrieved context) — structurally
    # independent of the LLM judges' shared training-data biases, per the
    # Independence-Aware Heterogeneous Evaluation line of work. Off by default —
    # adding a panel member changes every existing deployment's consensus numbers, so
    # this is opt-in rather than silently changing behavior for anyone already running
    # RAGeval. $0 either way (no API call) when turned on.
    RAGEVAL_INCLUDE_SYMBOLIC_JUDGE = os.getenv("RAGEVAL_INCLUDE_SYMBOLIC_JUDGE", "false").lower() == "true"

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


settings = Settings()
