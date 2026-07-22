"""Slim RAGeval configuration — env-driven."""
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
            "anthropic/claude-haiku-4-5,groq/llama-3.3-70b-versatile,gemini/gemini-1.5-flash",
        ).split(",") if m.strip()
    ]

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


settings = Settings()


# --- OPENAI TO GEMINI FALLBACK LOGIC ---
def _apply_gemini_fallback():
    openai_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    
    if not openai_key and gemini_key:
        def fallback(model_str):
            if model_str and ("openai" in model_str.lower() or "gpt-" in model_str.lower()):
                return "gemini/gemini-1.5-flash"
            return model_str
            
        for attr in dir(settings):
            if attr.startswith("LLM_") and isinstance(getattr(settings, attr), str):
                setattr(settings, attr, fallback(getattr(settings, attr)))
        
        if hasattr(settings, "JUDGE_MODELS") and isinstance(settings.JUDGE_MODELS, list):
            settings.JUDGE_MODELS = [fallback(m) for m in settings.JUDGE_MODELS]

_apply_gemini_fallback()
