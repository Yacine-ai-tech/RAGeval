"""
RAGeval configuration — runtime settings loaded from environment variables.

All API keys and secrets must be supplied via environment variables.
Defaults are safe for local development; always override in production.
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


class Settings:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    LOGS_DIR = str(LOGS_DIR)

    # CORS: comma-separated allowed origins. Empty -> "*" (dev). Set in production.
    CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",") if o.strip()]

    RAGEVAL_STORE = os.getenv("RAGEVAL_STORE", "sqlite")
    RAGEVAL_DB_PATH = os.getenv("RAGEVAL_DB_PATH", str(RAGEVAL_HOME / "rageval.db"))
    POSTGRES_URL = os.getenv("POSTGRES_URL", "")
    RAGEVAL_OTEL_ENDPOINT = os.getenv("RAGEVAL_OTEL_ENDPOINT", "")

    LLM_DEFAULT = os.getenv("LLM_DEFAULT", "groq/llama-3.3-70b-versatile")
    LLM_JUDGE = os.getenv("LLM_JUDGE", "anthropic/claude-haiku-4-5")

    JUDGE_MODELS = [
        m.strip() for m in os.getenv(
            "JUDGE_MODELS",
            "anthropic/claude-haiku-4-5,groq/llama-3.3-70b-versatile,openai/gpt-4o-mini",
        ).split(",") if m.strip()
    ]

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    INFERENCE_MODE = os.getenv("INFERENCE_MODE", "remote")
    EMBEDDING_ENDPOINT = os.getenv("EMBEDDING_ENDPOINT", "https://api-inference.huggingface.co/models/BAAI/bge-m3")
    INFERENCE_TOKEN = os.getenv("INFERENCE_TOKEN", "")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


settings = Settings()


def _validate_keys():
    keys = [
        settings.GROQ_API_KEY,
        settings.ANTHROPIC_API_KEY,
        settings.OPENAI_API_KEY,
        settings.GEMINI_API_KEY,
    ]
    set_keys_count = sum(1 for k in keys if k)
    if set_keys_count < 2:
        print("Warning: Fewer than 2 LLM API keys configured (GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY).")


_validate_keys()


