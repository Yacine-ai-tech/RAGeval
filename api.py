"""
RAGeval API — drop-in LLMOps observability.

Endpoints:
  GET  /health
  POST /eval/log
  POST /eval/score
  GET  /eval/metrics?days=7
  GET  /eval/queries?limit=50&needs_review=true
  GET  /eval/cost-report?days=30
  GET  /eval/alerts
  POST /eval/retrieval-bench
  POST /eval/embedding-comparison
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import settings
from core.logger import get_logger

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rageval.evaluator import RAGEvaluator
from rageval.store import (
    get_cost_report,
    get_metrics,
    get_query_log,
    init_rageval_table,
    log_interaction,
)

log = get_logger(__name__)

app = FastAPI(title="RAGeval", version="0.1.0", description="Drop-in LLMOps observability.")

# --- ETHICAL TELEMETRY ---
import threading
import requests
import os
import logging

def _send_telemetry():
    if os.environ.get("TELEMETRY_OPT_OUT", "").lower() in ("1", "true", "yes"):
        return
    try:
        logging.info("📡 Anonymous usage telemetry is ENABLED. This helps us understand project usage.")
        logging.info("📡 To disable this, set the environment variable TELEMETRY_OPT_OUT=true.")
        requests.post(
            "https://gateway.ysiddo-ai-projects.app/telemetry", 
            json={"service": "RAGeval", "event": "startup"},
            timeout=2
        )
    except Exception:
        pass

threading.Thread(target=_send_telemetry, daemon=True).start()
# -------------------------


from fastapi import Request
from fastapi.responses import JSONResponse
import os as _os

@app.middleware("http")
async def verify_internal_token(request: Request, call_next):
    # Allow health checks and public auth routes
    if request.url.path in ["/health", "/docs", "/openapi.json", "/api/redoc"] or request.url.path.startswith("/api/v1/auth/"):
        return await call_next(request)
        
    token = request.headers.get("X-OmniIntel-Internal-Token")
    expected_token = _os.environ.get("OMNIINTEL_INTERNAL_TOKEN", "default-dev-token")
    
    if token != expected_token and _os.environ.get("REQUIRE_INTERNAL_TOKEN", "true").lower() == "true":
        return JSONResponse(status_code=403, content={"detail": "Missing or invalid X-OmniIntel-Internal-Token"})
        
    return await call_next(request)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ALLOWED_ORIGINS or ["*"],
                   allow_methods=["*"], allow_headers=["*"])

try:  # browser demo UI (served by the backend, no separate deploy)
    app.mount("/demo", StaticFiles(directory="demo", html=True), name="demo")
except RuntimeError:
    log.warning("demo/ directory not found — /demo will not be served")

try:
    _assets_dir = _os.path.join(_os.path.dirname(__file__), "frontend", "dist", "assets")
    if _os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
except Exception as e:
    log.warning("assets mount failed: %s", e)

evaluator = RAGEvaluator()

# In-memory telemetry ring — real events emitted by the evaluation pipeline (v1 "Live
# Traces"/observability ask). Process-local by design; /eval/events exposes it.
from collections import deque as _deque
from datetime import datetime as _dt

_EVENTS: "_deque[Dict[str, Any]]" = _deque(maxlen=200)

def _emit(kind: str, **detail: Any) -> None:
    _EVENTS.appendleft({"ts": _dt.utcnow().isoformat() + "Z", "kind": kind, **detail})


@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the accessible RAGeval dashboard at the root."""
    import os
    root = os.path.dirname(__file__)
    spa = os.path.join(root, "frontend", "dist", "index.html")
    if os.path.exists(spa):
        return FileResponse(spa)
    path = os.path.join(root, "demo", "index.html")
    return FileResponse(path) if os.path.exists(path) else {"service": "rageval", "docs": "/docs"}


# Initialize DB on import
try:
    init_rageval_table()
except Exception as e:
    log.warning("DB init failed at import: %s", e)


class LogRequest(BaseModel):
    query: str
    answer: str
    chunks: List[str] = []
    contexts: List[str] = []   # accepted alias for `chunks`
    tokens_used: int = 0
    latency_ms: float = 0.0
    model: str = "groq/llama-3.3-70b-versatile"
    persona: Optional[str] = None
    session_id: Optional[str] = None


class ScoreRequest(BaseModel):
    query: str
    answer: str
    chunks: List[str] = []
    contexts: List[str] = []   # accepted alias for `chunks` (clients use either name)
    tokens_used: int = 0
    latency_ms: float = 0.0
    model: str = "groq/llama-3.3-70b-versatile"
    persona: Optional[str] = None


class RetrievalBenchRequest(BaseModel):
    queries: List[str]
    chunks_a: List[List[str]]  # one list per query for strategy A
    chunks_b: List[List[str]]


class EmbeddingComparisonRequest(BaseModel):
    queries: List[str]
    chunks: List[List[str]]
    embedding_models: List[str] = ["BAAI/bge-large-en-v1.5", "sentence-transformers/all-MiniLM-L6-v2"]


# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "rageval", "version": "0.1.0"}


@app.post("/eval/log")
async def eval_log(req: LogRequest) -> Dict[str, Any]:
    _emit("interaction.received", route="/eval/log", query=req.query[:120], persona=req.persona)
    scores = await evaluator.score_interaction(
        query=req.query, answer=req.answer, chunks=req.chunks or req.contexts,
        tokens_used=req.tokens_used, latency_ms=req.latency_ms,
        model=req.model, persona=req.persona,
    )
    await log_interaction(req.query, req.answer, req.persona, scores, req.session_id)
    c = scores.get("groundedness_consensus", {})
    _emit("interaction.scored", route="/eval/log", overall=scores.get("overall_quality"),
          judges_used=c.get("judges_used"), flags=scores.get("flags"), persisted=True)
    return scores


@app.post("/eval/score")
async def eval_score(req: ScoreRequest) -> Dict[str, Any]:
    _emit("interaction.received", route="/eval/score", query=req.query[:120], persona=req.persona)
    scores = await evaluator.score_interaction(
        query=req.query, answer=req.answer, chunks=req.chunks or req.contexts,
        tokens_used=req.tokens_used, latency_ms=req.latency_ms,
        model=req.model, persona=req.persona,
    )
    c = scores.get("groundedness_consensus", {})
    _emit("interaction.scored", route="/eval/score", overall=scores.get("overall_quality"),
          judges_used=c.get("judges_used"), flags=scores.get("flags"), persisted=False)
    return scores


@app.get("/eval/events")
async def eval_events(limit: int = 100) -> Dict[str, Any]:
    """Live telemetry: the most recent evaluation-pipeline events (in-memory ring)."""
    return {"events": list(_EVENTS)[:limit], "capacity": _EVENTS.maxlen}


@app.get("/eval/config")
async def eval_config() -> Dict[str, Any]:
    """Factual evaluator configuration (no secrets): judges, embedding model, thresholds."""
    return {
        "judge_models": settings.JUDGE_MODELS,
        "embedding_model": getattr(settings, "EMBEDDING_MODEL", None),
        "disagreement_stdev_threshold": 0.2,
        "review_flags": ["LOW_RETRIEVAL_RELEVANCE", "POTENTIAL_HALLUCINATION",
                          "HIGH_LATENCY", "JUDGE_DISAGREEMENT", "PERSONA_SCOPE_VIOLATION"],
    }


@app.get("/eval/metrics")
async def eval_metrics(days: int = 7) -> Dict[str, Any]:
    return get_metrics(days=days)


@app.get("/eval/queries")
async def eval_queries(limit: int = 50, needs_review: Optional[bool] = None) -> List[Dict[str, Any]]:
    return get_query_log(limit=limit, needs_review=needs_review)


@app.get("/eval/cost-report")
async def eval_cost_report(days: int = 30) -> Dict[str, Any]:
    return get_cost_report(days=days)


@app.get("/eval/alerts")
async def eval_alerts() -> Dict[str, Any]:
    flagged = get_query_log(limit=50, needs_review=True)
    return {"flagged_count": len(flagged), "alerts": flagged[:10]}


@app.post("/eval/retrieval-bench")
async def retrieval_bench(req: RetrievalBenchRequest) -> Dict[str, Any]:
    if not (len(req.queries) == len(req.chunks_a) == len(req.chunks_b)):
        raise HTTPException(status_code=400, detail="length_mismatch")
    a_scores = [evaluator.score_retrieval_relevance(q, cs) for q, cs in zip(req.queries, req.chunks_a)]
    b_scores = [evaluator.score_retrieval_relevance(q, cs) for q, cs in zip(req.queries, req.chunks_b)]
    return {
        "strategy_a_mean": sum(a_scores) / max(len(a_scores), 1),
        "strategy_b_mean": sum(b_scores) / max(len(b_scores), 1),
        "winner": "a" if sum(a_scores) >= sum(b_scores) else "b",
        "per_query_a": a_scores,
        "per_query_b": b_scores,
    }


@app.post("/eval/embedding-comparison")
async def embedding_comparison(req: EmbeddingComparisonRequest) -> Dict[str, Any]:
    results: Dict[str, float] = {}
    for model in req.embedding_models:
        ev = RAGEvaluator(embedding_model=model)
        scores = [ev.score_retrieval_relevance(q, cs) for q, cs in zip(req.queries, req.chunks)]
        results[model] = sum(scores) / max(len(scores), 1)
    return {"results": results, "best": max(results, key=results.get) if results else None}



