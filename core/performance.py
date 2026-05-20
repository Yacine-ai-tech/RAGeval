"""
⚡ PERFORMANCE CONFIGURATION — Optimizations for Lightning-Fast Startup

This module contains performance tuning settings to achieve:
- Sub-second application startup
- Minimal memory footprint
- Efficient resource utilization
- Lazy loading of heavy dependencies
"""
from __future__ import annotations

import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# STARTUP OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

# Disable heavy library initializations at import time
os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")  # Allow online but don't preload
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")  # Disable telemetry
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # Avoid warnings

# PyTorch optimizations
os.environ.setdefault("OMP_NUM_THREADS", "4")  # Limit CPU threads
os.environ.setdefault("MKL_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "4")

# Disable CUDA if not needed (forces CPU mode for faster startup)
# Uncomment the line below to force CPU-only mode:
# os.environ["CUDA_VISIBLE_DEVICES"] = ""

# ═══════════════════════════════════════════════════════════════════════════
# CACHE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

# Cache directories
CACHE_DIR = Path.home() / ".cache" / "omniintelos"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MODEL_CACHE_DIR = CACHE_DIR / "models"
MODEL_CACHE_DIR.mkdir(exist_ok=True)

# Set Hugging Face cache location
os.environ.setdefault("HF_HOME", str(MODEL_CACHE_DIR))
os.environ.setdefault("TRANSFORMERS_CACHE", str(MODEL_CACHE_DIR / "transformers"))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(MODEL_CACHE_DIR / "sentence-transformers"))

# ═══════════════════════════════════════════════════════════════════════════
# LAZY LOADING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Which models to preload in background (empty list = fastest startup)
PRELOAD_MODELS = []  # Options: ["groq", "sentence_transformer", "tavily"]

# Enable/disable features for faster startup
ENABLE_ML_FEATURES = True  # Set to False to disable all ML features
ENABLE_WEB_SEARCH = True   # Set to False to disable web search
ENABLE_RAG = True          # Set to False to disable RAG

# ═══════════════════════════════════════════════════════════════════════════
# MEMORY OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

# Maximum cache sizes
MAX_CONVERSATION_CACHE = 100  # Number of conversations to keep in memory
MAX_DOCUMENT_CACHE = 50       # Number of documents to keep in memory
MAX_MODEL_CACHE = 2           # Number of models to keep loaded

# Batch sizes for processing
BATCH_SIZE = 32              # For embeddings
MAX_TOKENS_PER_REQUEST = 4096  # Maximum tokens in single request

# ═══════════════════════════════════════════════════════════════════════════
# CONCURRENCY SETTINGS
# ═══════════════════════════════════════════════════════════════════════════

# Worker threads for async operations
MAX_WORKERS = 4
THREAD_POOL_SIZE = 4

# Uvicorn server settings (for FastAPI)
UVICORN_WORKERS = 1  # Single worker for development
UVICORN_TIMEOUT = 30
UVICORN_KEEPALIVE = 5

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

# Reduce logging overhead
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = False  # Disable file logging for faster startup
LOG_FORMAT = "simple"  # Options: simple, detailed, json

# Suppress noisy library logs
SUPPRESS_WARNINGS = True
if SUPPRESS_WARNINGS:
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    
    # Suppress specific library warnings
    import logging
    logging.getLogger("transformers").setLevel(logging.ERROR)
    logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
    logging.getLogger("torch").setLevel(logging.ERROR)
    logging.getLogger("tensorflow").setLevel(logging.ERROR)

# ═══════════════════════════════════════════════════════════════════════════
# DATABASE OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

# Connection pooling
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600

# Query optimization
DB_ECHO = False  # Disable SQL query logging
DB_BATCH_SIZE = 100

# ═══════════════════════════════════════════════════════════════════════════
# API OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

# Request timeouts
API_TIMEOUT = 30  # seconds
LLM_TIMEOUT = 60  # seconds for LLM calls
EMBEDDING_TIMEOUT = 120  # seconds for embedding generation

# Rate limiting
RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_BURST = 10

# ═══════════════════════════════════════════════════════════════════════════
# DEVELOPMENT MODE
# ═══════════════════════════════════════════════════════════════════════════

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

if DEV_MODE:
    # Enable debug features in development
    LOG_LEVEL = "DEBUG"
    LOG_TO_FILE = True
    SUPPRESS_WARNINGS = False
    UVICORN_WORKERS = 1
