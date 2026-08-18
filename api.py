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
  GET  /eval/events
  GET  /eval/config
  POST /eval/retrieval-bench
  POST /eval/embedding-comparison
  WS   /eval/live
"""
from __future__ import annotations
import base64

import os as _os_early

# One-time compat shim, scoped to this standalone-app process only: older/existing
# deployments may still set POSTGRES_URL directly (e.g. via a hosting platform's own
# dashboard env-var UI) rather than the newer RAGEVAL_POSTGRES_URL. core/config.py and
# rageval/_compat.py deliberately no longer fall back to POSTGRES_URL themselves — that
# fallback is what made `rageval`, when imported as a *library* elsewhere, silently
# adopt a host app's own unrelated database. Doing the compat copy here instead, before
# either settings module is imported, keeps that safety while not breaking existing
# deployments of this standalone app.
if not _os_early.environ.get("RAGEVAL_POSTGRES_URL") and _os_early.environ.get("POSTGRES_URL"):
    _os_early.environ["RAGEVAL_POSTGRES_URL"] = _os_early.environ["POSTGRES_URL"]

import asyncio
import time
import threading
import uuid as _uuid
from collections import deque as _deque
from datetime import datetime as _dt
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import settings
from core.logger import get_logger

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from rageval.evaluator import RAGEvaluator, InsufficientJudgesError
from rageval.store import (
    get_cost_report,
    get_metrics,
    get_query_log,
    init_rageval_table,
    log_interaction,
)

# Rate limiting: prevents LLM judge quota exhaustion from unauthenticated clients.
# Each /eval/score or /eval/log call triggers multiple LLM judge calls; without limiting,
# a single actor could exhaust the configured judge providers' quotas in under a minute.
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _limiter = Limiter(key_func=get_remote_address)
    _RATE_LIMIT_ENABLED = True
except ImportError:
    _limiter = None
    _RATE_LIMIT_ENABLED = False

log = get_logger(__name__)

# Read the real installed package version rather than hardcoding one.
try:
    from importlib.metadata import version as _pkg_version
    _VERSION = _pkg_version("omnismart-rageval")
except Exception:
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # fallback for < 3.11
    try:
        _pyproject = os.path.join(os.path.dirname(__file__), "pyproject.toml")
        with open(_pyproject, "rb") as _f:
            _VERSION = tomllib.load(_f).get("project", {}).get("version", "unknown")
    except Exception:
        _VERSION = "unknown"

app = FastAPI(title="RAGeval", version=_VERSION, description="Drop-in LLMOps observability.")

# Attach the rate limiter to the app.
if _RATE_LIMIT_ENABLED:
    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ─── Telemetry ────────────────────────────────────────────────────────────────

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
    if os.environ.get("TELEMETRY_OPT_OUT", "false").lower() == "true":
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

    telemetry_url = os.environ.get("TELEMETRY_URL", "")
    if not telemetry_url:
        return
    try:
        log.info(
            "Anonymous telemetry ping to %s (set TELEMETRY_OPT_OUT=true to disable).",
            telemetry_url,
        )
        requests.post(
            telemetry_url,
            json={"service": "RAGeval", "event": "startup", "instance_id": _telemetry_instance_id()},
            timeout=2,
        )
    except Exception:
        pass


threading.Thread(target=_send_telemetry, daemon=True).start()

# ─── Middleware ───────────────────────────────────────────────────────────────

@app.middleware("http")
async def verify_internal_token(request: Request, call_next):
    """Token gate for service-to-service calls.

    The /eval/* API prefix is explicitly allowed through for browser clients
    (GET endpoints). Only write endpoints that could drain LLM quota (POST
    /eval/log, POST /eval/score, POST /eval/retrieval-bench, POST
    /eval/embedding-comparison) require the internal token when
    REQUIRE_INTERNAL_TOKEN=true is set.

    This two-tier policy lets:
    - The dashboard (browser, no token) read all GET /eval/* data freely.
    - Trusted service-to-service callers (with the token) write evaluations.
    - External @track integrations (pip users) POST with the token.
    """
    path = request.url.path
    method = request.method

    # Always pass: OPTIONS (CORS preflight), docs, static SPA assets, health.
    _public = (
        method == "OPTIONS"
        or path in {"/", "/health", "/docs", "/openapi.json", "/api/redoc",
                    "/favicon.png", "/favicon.ico", "/mark.png", "/logo.png"}
        or path.startswith("/assets/")
        or path.startswith("/static/")
    )
    if _public:
        return await call_next(request)

    # All GET /eval/* routes are readable without the token
    # (they are displayed in the public-facing browser dashboard).
    # Only POST (write/score) routes require the internal token.
    _eval_get = path.startswith("/eval/") and method == "GET"
    if _eval_get:
        return await call_next(request)

    # WebSocket /eval/live — no token needed (real-time dashboard feed).
    if path == "/eval/live":
        return await call_next(request)

    # POST/write routes: enforce token when REQUIRE_INTERNAL_TOKEN=true.
    token = request.headers.get("X-OmniIntel-Internal-Token")
    expected = os.environ.get("OMNIINTEL_INTERNAL_TOKEN", "")
    if os.environ.get("REQUIRE_INTERNAL_TOKEN", "false").lower() == "true":
        if not expected or token != expected:
            return JSONResponse(
                status_code=403,
                content={"detail": "Missing or invalid X-OmniIntel-Internal-Token"},
            )

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static assets ────────────────────────────────────────────────────────────

try:
    _assets_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist", "assets")
    if os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
except Exception as e:
    log.warning("assets mount failed: %s", e)

evaluator = RAGEvaluator()

# ─── Telemetry ring + WebSocket broadcast ────────────────────────────────────
# Process-local by design; /eval/events exposes recent events via GET (polling)
# and /eval/live exposes them via WebSocket (push).

_EVENTS: "_deque[Dict[str, Any]]" = _deque(maxlen=200)

# events/detail (query text, persona) are real visitor content, same as rageval_log —
# events carry a session_id (None for global/service-to-service callers, same
# "no session, no restriction" default used throughout this file) and both the GET
# poll and the WS push below filter on it before a caller ever sees another
# visitor's query text.
#
# _WS_CLIENTS is accessed from async handlers only (the route coroutines all run
# on the same uvicorn event loop thread), so asyncio.Lock() is the correct
# synchronisation primitive here — no threading.Lock() needed. _emit() schedules
# the broadcast as a coroutine on the running loop rather than calling
# ws.send_json directly, so all mutations of _WS_CLIENTS happen inside async
# handlers only, even when _emit() itself is called from a sync code path.
_WS_CLIENTS: Dict[Any, Optional[str]] = {}  # websocket -> that connection's session_id
_ws_lock = asyncio.Lock()


def _event_visible(event: Dict[str, Any], session_id: Optional[str]) -> bool:
    ev_session = event.get("session_id")
    return ev_session is None or ev_session == session_id


def _emit(kind: str, session_id: Optional[str] = None, **detail: Any) -> None:
    from datetime import timezone
    event = {"ts": _dt.now(timezone.utc).isoformat(), "kind": kind, "session_id": session_id, **detail}
    _EVENTS.appendleft(event)
    # Schedule broadcast without touching _WS_CLIENTS from a potentially
    # non-event-loop context — the async _broadcast() coroutine owns the lock.
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_broadcast(event))
    except RuntimeError:
        pass  # no running loop (test/import context) — skip broadcast


async def _broadcast(event: Dict[str, Any]) -> None:
    """Send event to connected WebSocket clients allowed to see it (async, lock-protected)."""
    async with _ws_lock:
        disconnected = []
        for ws, ws_session_id in list(_WS_CLIENTS.items()):  # snapshot — safe even if lock broken
            if not _event_visible(event, ws_session_id):
                continue
            try:
                await ws.send_json(event)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            _WS_CLIENTS.pop(ws, None)


@app.websocket("/eval/live")
async def eval_live_ws(websocket: WebSocket):
    session_id = websocket.headers.get("x-demo-session-id")
    await websocket.accept()
    async with _ws_lock:
        _WS_CLIENTS[websocket] = session_id
    try:
        for event in list(_EVENTS):
            if _event_visible(event, session_id):
                await websocket.send_json(event)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with _ws_lock:
            _WS_CLIENTS.pop(websocket, None)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the accessible RAGeval dashboard at the root."""
    root = os.path.dirname(__file__)
    spa = os.path.join(root, "frontend", "dist", "index.html")
    if os.path.exists(spa):
        return FileResponse(spa)
    return {"service": "rageval", "docs": "/docs"}


# ─── DB init ─────────────────────────────────────────────────────────────────

try:
    init_rageval_table()
except Exception as e:
    log.warning("DB init failed at import: %s", e)


# ─── Request models ──────────────────────────────────────────────────────────

class LogRequest(BaseModel):
    query: str
    answer: str
    chunks: List[str] = []
    contexts: List[str] = []   # accepted alias for `chunks`
    tokens_used: int = 0
    latency_ms: float = 0.0
    model: str = "groq/openai/gpt-oss-120b"
    persona: Optional[str] = None
    session_id: Optional[str] = None


class ScoreRequest(BaseModel):
    query: str
    answer: str
    chunks: List[str] = []
    contexts: List[str] = []   # accepted alias for `chunks` (clients use either name)
    tokens_used: int = 0
    latency_ms: float = 0.0
    model: str = "groq/openai/gpt-oss-120b"
    persona: Optional[str] = None


class RetrievalBenchRequest(BaseModel):
    queries: List[str]
    chunks_a: List[List[str]]  # ranked chunk text per query, strategy A (best first)
    chunks_b: List[List[str]]  # ranked chunk text per query, strategy B
    # Ground-truth relevant chunk text per query, optional. When given, enables
    # precision@k / recall@k / MRR (standard IR ranking metrics) in addition to the
    # embedding-similarity relevance score, which is always computed and needs no labels.
    relevant_chunks: Optional[List[List[str]]] = None
    precision_k: int = 5
    recall_k: int = 10


class EmbeddingComparisonRequest(BaseModel):
    queries: List[str]
    chunks: List[List[str]]
    embedding_models: List[str] = ["BAAI/bge-m3", "sentence-transformers/all-MiniLM-L6-v2"]


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "rageval", "version": _VERSION}


def _resolve_session_id(request: Request, body_session_id: Optional[str] = None) -> Optional[str]:
    """A visitor's own browser sends X-Demo-Session-Id (set by the frontend); that takes
    precedence since it can't be spoofed by a request body field. Service-to-service callers
    have no browser session and pass session_id in the body instead — their rows stay
    platform-visible rather than scoped to a single anonymous demo session."""
    return request.headers.get("X-Demo-Session-Id") or body_session_id


@app.post("/eval/log")
async def eval_log(req: LogRequest, request: Request) -> Dict[str, Any]:
    # Rate-limit write endpoints that trigger LLM judge calls.
    if _RATE_LIMIT_ENABLED and _limiter:
        await _limiter._check_request_limit(request, eval_log, "60/minute")  # type: ignore[arg-type]
    session_id = _resolve_session_id(request, req.session_id)
    _emit("interaction.received", route="/eval/log", query=req.query[:120], persona=req.persona, session_id=session_id)
    try:
        scores = await evaluator.score_interaction(
            query=req.query, answer=req.answer, chunks=req.chunks or req.contexts,
            tokens_used=req.tokens_used, latency_ms=req.latency_ms,
            model=req.model, persona=req.persona,
        )
    except InsufficientJudgesError as e:
        raise HTTPException(status_code=503, detail=str(e))
    await log_interaction(req.query, req.answer, req.persona, scores, session_id)
    c = scores.get("groundedness_consensus", {})
    _emit("interaction.scored", route="/eval/log", overall=scores.get("overall_quality"),
          judges_used=c.get("judges_used"), flags=scores.get("flags"), persisted=True, session_id=session_id)
    return scores


@app.post("/eval/score")
async def eval_score(req: ScoreRequest, request: Request) -> Dict[str, Any]:
    # Rate-limit score endpoint — each call triggers multiple LLM judge calls.
    if _RATE_LIMIT_ENABLED and _limiter:
        await _limiter._check_request_limit(request, eval_score, "60/minute")  # type: ignore[arg-type]
    session_id = _resolve_session_id(request, None)
    _emit("interaction.received", route="/eval/score", query=req.query[:120], persona=req.persona, session_id=session_id)
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
          judges_used=c.get("judges_used"), flags=scores.get("flags"), persisted=False, session_id=session_id)
    return scores


@app.get("/eval/events")
async def eval_events(
    limit: int = 100,
    x_demo_session_id: Optional[str] = Header(default=None, alias="X-Demo-Session-Id"),
) -> Dict[str, Any]:
    """Live telemetry: the most recent evaluation-pipeline events (in-memory ring).
    Scoped like everything else here — see _event_visible."""
    visible = [e for e in _EVENTS if _event_visible(e, x_demo_session_id)]
    return {"events": visible[:limit], "capacity": _EVENTS.maxlen}


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
    n = len(req.queries)
    if not (n == len(req.chunks_a) == len(req.chunks_b)):
        raise HTTPException(status_code=400, detail="length_mismatch")
    if req.relevant_chunks is not None and len(req.relevant_chunks) != n:
        raise HTTPException(status_code=400, detail="relevant_chunks_length_mismatch")

    # A single reusable helper — the A/B difference is purely in the input data
    # (chunks_a vs chunks_b), not in the scoring strategy.
    async def _score_chunks(q, cs):
        return await asyncio.to_thread(evaluator.score_retrieval_relevance, q, cs)

    a_relevance = await asyncio.gather(*[_score_chunks(q, cs) for q, cs in zip(req.queries, req.chunks_a)])
    b_relevance = await asyncio.gather(*[_score_chunks(q, cs) for q, cs in zip(req.queries, req.chunks_b)])

    def _ranking_summary(chunks_per_query: List[List[str]]) -> Optional[Dict[str, Any]]:
        if req.relevant_chunks is None:
            return None
        per_query = [
            RAGEvaluator.score_ranking(cs, rel, req.precision_k, req.recall_k)
            for cs, rel in zip(chunks_per_query, req.relevant_chunks)
        ]
        m = max(len(per_query), 1)
        return {
            "precision_at_k": sum(q["precision_at_k"] for q in per_query) / m,
            "recall_at_k": sum(q["recall_at_k"] for q in per_query) / m,
            "mrr": sum(q["reciprocal_rank"] for q in per_query) / m,
            "per_query": per_query,
        }

    a_ranking = _ranking_summary(req.chunks_a)
    b_ranking = _ranking_summary(req.chunks_b)
    a_mean = sum(a_relevance) / max(len(a_relevance), 1)
    b_mean = sum(b_relevance) / max(len(b_relevance), 1)

    # Winner: when ground truth was supplied, decide on ranking quality (precision/recall
    # F1 @k) rather than embedding similarity — that's the whole point of providing labels.
    if a_ranking is not None and b_ranking is not None:
        def _f1(ranking: Dict[str, Any]) -> float:
            p, r = ranking["precision_at_k"], ranking["recall_at_k"]
            return 2 * p * r / (p + r) if (p + r) else 0.0
        winner = "a" if _f1(a_ranking) >= _f1(b_ranking) else "b"
    else:
        winner = "a" if a_mean >= b_mean else "b"

    def _strategy_result(mean_relevance: float, per_query_relevance: List[float],
                          ranking: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "mean_relevance": mean_relevance,
            "per_query_relevance": per_query_relevance,
        }
        if ranking is not None:
            result["precision_at_k"] = ranking["precision_at_k"]
            result["recall_at_k"] = ranking["recall_at_k"]
            result["mrr"] = ranking["mrr"]
            result["per_query_ranking"] = ranking["per_query"]
        return result

    return {
        "strategy_a": _strategy_result(a_mean, a_relevance, a_ranking),
        "strategy_b": _strategy_result(b_mean, b_relevance, b_ranking),
        "winner": winner,
        "has_ground_truth": req.relevant_chunks is not None,
        "precision_k": req.precision_k,
        "recall_k": req.recall_k,
    }


@app.post("/eval/embedding-comparison")
async def embedding_comparison(req: EmbeddingComparisonRequest) -> Dict[str, Any]:
    results: Dict[str, float] = {}

    async def _eval_model(model):
        ev = RAGEvaluator(embedding_model=model)
        scores = await asyncio.gather(
            *[asyncio.to_thread(ev.score_retrieval_relevance, q, cs)
              for q, cs in zip(req.queries, req.chunks)]
        )
        return model, sum(scores) / max(len(scores), 1)

    res = await asyncio.gather(*[_eval_model(m) for m in req.embedding_models])
    for model, score in res:
        results[model] = score

    return {"results": results, "best": max(results, key=results.get) if results else None}


# ─── SPA fallback (must be last) ─────────────────────────────────────────────

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Catch-all so direct navigation, refresh, or a bookmarked/shared link to
    any frontend route serves the SPA instead of a raw 404 -- React Router
    then resolves the route client-side. Declared last so every real API/WS
    route above still wins.

    Real static files in frontend/dist/ (favicon, logo, sw.js, ...) are
    served directly rather than falling back to index.html for them.
    """
    root = os.path.dirname(__file__)
    dist = os.path.realpath(os.path.join(root, "frontend", "dist"))
    candidate = os.path.realpath(os.path.join(dist, full_path))
    if candidate.startswith(dist + os.sep) and os.path.isfile(candidate):
        return FileResponse(candidate)
    spa = os.path.join(dist, "index.html")
    if os.path.exists(spa):
        return FileResponse(spa)
    raise HTTPException(status_code=404, detail="Not Found")
