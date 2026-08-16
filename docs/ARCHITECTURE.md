# RAGeval Architecture & Implementation Status

## 1. System Overview
RAGeval is a self-hosted, drop-in LLMOps observability tool. It operates as a FastAPI backend with a React SPA dashboard designed to track relevance, groundedness, latency, cost, and persona-adherence of RAG queries. Developers integrate it into their own apps via a simple Python `@track` decorator with zero config. Data flows into SQLite (default) or Postgres (production, via pgvector) and is scored asynchronously by a multi-judge consensus engine.

## 2. Compliance with Strategy
- **Multi-judge consensus:** ✅ Implemented in `_compat.py` utilizing a mix of frontier models (Haiku, Llama 3.3, GPT-5-mini/Gemini-Flash).
- **Domain-aware metrics:** ✅ The evaluator explicitly scores for `PERSONA_SCOPE_VIOLATION`.
- **OpenTelemetry export:** ✅ Standard OTLP spans are implemented in `src/rageval/otel_exporter.py`.
- **DSPy & Benchmarks:** ✅ Benchmarks (`/eval/retrieval-bench`, `/eval/embedding-comparison`) and DSPy bindings are fully integrated.
- **Standalone & GPU constraints:** ✅ Uses `RAGEVAL_POSTGRES_URL` to intentionally avoid colliding with a host app's generic Postgres DB. GPU compute is highly configurable via `USE_LOCAL_EMBEDDER` (local torch) vs `INFERENCE_MODE=remote` (avoids vendor lock-in).

## 3. Current State & Known Drift
- **What's confirmed working:** The core observability pipeline, multi-judge engine, DSPy/OpenTelemetry integrations, and frontend UI routing.
- **Known Drift:** The `/eval/live` WebSocket architecture described in the strategy was superseded by a simpler, more robust HTTP polling mechanism (`/eval/events`).

## 4. Production Deployment
The `Dockerfile` and `render.yaml` configurations are cleanly aligned with the `uvicorn` entry points. The SPA route fallback (`spa_fallback` in `api.py`) ensures that deep-linking on production Render deployments works correctly without hitting a 404.
