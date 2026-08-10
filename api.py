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

from rageval.evaluator import RAGEvaluator, InsufficientJudgesError
from rageval.store import (
    get_cost_report,
    get_metrics,
    get_query_log,
    init_rageval_table,
    log_interaction,
)

log = get_logger(__name__)

app = FastAPI(title="RAGeval", version="0.1.0", description="Drop-in LLMOps observability.")

# --- ETHICAL TELEMETRY (see TELEMETRY.md) ---
import threading
import requests
import os
import time
import uuid as _uuid


def _telemetry_instance_id() -> str:
    """
    A random, locally-generated install ID — NOT derived from MAC address or any other
    hardware fingerprint. Persisted under LOGS_DIR so repeat startups of the same install
    report the same ID (for dedup on the receiving end); delete the file to reset it.
    See TELEMETRY.md for why this is a random UUID rather than a hardware-derived value.
    """
    id_file = os.path.join(settings.LOGS_DIR, ".telemetry_instance_id")
    try:
        if os.path.exists(id_file):
            existing = open(id_file).read().strip()
            if existing:
                return existing
    except Exception:
        pass
    new_id = _uuid.uuid4().hex[:16]
    try:
        with open(id_file, "w") as f:
            f.write(new_id)
    except Exception:
        pass
    return new_id


def _send_telemetry():
    if os.environ.get("TELEMETRY_OPT_OUT", "").lower() in ("1", "true", "yes"):
        return

    lock_file = os.path.join(settings.LOGS_DIR, ".telemetry_last_ping")
    try:
        if os.path.exists(lock_file):
            if time.time() - os.path.getmtime(lock_file) < 21600:
                return
        with open(lock_file, "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass

    try:
        telemetry_url = os.environ.get(
            "TELEMETRY_URL", "https://gateway.ysiddo-ai-projects.app/telemetry"
        )
        if "log" in globals():
            globals()["log"].info(
                "Anonymous telemetry ping to %s (set TELEMETRY_OPT_OUT=true to disable).", telemetry_url
            )
        else:
            import logging
            logging.info(
                "Anonymous telemetry ping to %s (set TELEMETRY_OPT_OUT=true to disable).", telemetry_url
            )

        requests.post(
            telemetry_url,
            json={"service": "RAGeval", "event": "startup", "instance_id": _telemetry_instance_id()},
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
    # Allow health checks. The /api/v1/auth/ exemption is shared boilerplate with the
    # other OmniIntel services (IntelAI defines real routes there) — RAGeval itself has
    # no such routes, so this branch is a no-op here, not a live auth bypass.
    if request.url.path in ["/health", "/docs", "/openapi.json", "/api/redoc"] or request.url.path.startswith("/api/v1/auth/"):
        return await call_next(request)
        
    token = request.headers.get("X-OmniIntel-Internal-Token")
    expected_token = _os.environ.get("OMNIINTEL_INTERNAL_TOKEN", "")
    
    if token != expected_token and _os.environ.get("REQUIRE_INTERNAL_TOKEN", "true").lower() == "true":
        return JSONResponse(status_code=403, content={"detail": "Missing or invalid X-OmniIntel-Internal-Token"})
        
    return await call_next(request)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ALLOWED_ORIGINS or ["*"],
                   allow_methods=["*"], allow_headers=["*"])



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
    return {"service": "rageval", "docs": "/docs"}


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
    embedding_models: List[str] = ["BAAI/bge-m3", "sentence-transformers/all-MiniLM-L6-v2"]


# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "rageval", "version": "0.1.0"}


def _resolve_session_id(request: Request, body_session_id: Optional[str] = None) -> Optional[str]:
    """A visitor's own browser sends X-Demo-Session-Id (set by the frontend); that takes
    precedence since it can't be spoofed by a request body field. Service-to-service callers
    (e.g. IntelAI's own chatbot dogfooding its RAG quality into this table) have no browser
    session and pass session_id in the body instead — their rows stay platform-visible."""
    return request.headers.get("X-Demo-Session-Id") or body_session_id


@app.post("/eval/log")
async def eval_log(req: LogRequest, request: Request) -> Dict[str, Any]:
    _emit("interaction.received", route="/eval/log", query=req.query[:120], persona=req.persona)
    try:
        scores = await evaluator.score_interaction(
            query=req.query, answer=req.answer, chunks=req.chunks or req.contexts,
            tokens_used=req.tokens_used, latency_ms=req.latency_ms,
            model=req.model, persona=req.persona,
        )
    except InsufficientJudgesError as e:
        raise HTTPException(status_code=503, detail=str(e))
    session_id = _resolve_session_id(request, req.session_id)
    await log_interaction(req.query, req.answer, req.persona, scores, session_id)
    c = scores.get("groundedness_consensus", {})
    _emit("interaction.scored", route="/eval/log", overall=scores.get("overall_quality"),
          judges_used=c.get("judges_used"), flags=scores.get("flags"), persisted=True)
    return scores


@app.post("/eval/score")
async def eval_score(req: ScoreRequest) -> Dict[str, Any]:
    _emit("interaction.received", route="/eval/score", query=req.query[:120], persona=req.persona)
    try:
        scores = await evaluator.score_interaction(
            query=req.query, answer=req.answer, chunks=req.chunks or req.contexts,
            tokens_used=req.tokens_used, latency_ms=req.latency_ms,
            model=req.model, persona=req.persona,
        )
    except InsufficientJudgesError as e:
        raise HTTPException(status_code=503, detail=str(e))
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
async def eval_metrics(request: Request, days: int = 7) -> Dict[str, Any]:
    return get_metrics(days=days, session_id=_resolve_session_id(request))


@app.get("/eval/queries")
async def eval_queries(request: Request, limit: int = 50, needs_review: Optional[bool] = None) -> List[Dict[str, Any]]:
    return get_query_log(limit=limit, needs_review=needs_review, session_id=_resolve_session_id(request))


@app.get("/eval/cost-report")
async def eval_cost_report(request: Request, days: int = 30) -> Dict[str, Any]:
    return get_cost_report(days=days, session_id=_resolve_session_id(request))


@app.get("/eval/alerts")
async def eval_alerts(request: Request) -> Dict[str, Any]:
    flagged = get_query_log(limit=50, needs_review=True, session_id=_resolve_session_id(request))
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



