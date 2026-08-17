"""
RAGeval store — SQLite default, Postgres+pgvector optional.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rageval._compat import settings, get_logger  # self-contained (works when pip-installed)
from rageval.otel_exporter import init_otel, export_span

log = get_logger(__name__)


_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS rageval_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    query TEXT NOT NULL,
    answer TEXT,
    persona TEXT,
    model TEXT,
    relevance REAL,
    groundedness REAL,
    faithfulness REAL,
    cost_usd REAL,
    latency_ms REAL,
    tokens_used INTEGER,
    flags TEXT,
    session_id TEXT,
    needs_review INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_rageval_ts ON rageval_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_rageval_review ON rageval_log(needs_review);
CREATE INDEX IF NOT EXISTS idx_rageval_model ON rageval_log(model);
"""

def _schema_pg() -> str:
    """Postgres schema, production tier. Adds a pgvector column that stores each
    interaction's query embedding (populated in log_interaction when POSTGRES_URL is
    set — see evaluator.score_interaction), so retrieval-relevance queries can use
    Postgres-native vector similarity instead of recomputing embeddings from scratch.
    Requires the pgvector extension (Postgres 13+, pgvector 0.5+ for the HNSW index).

    The embedding column and its index are added via ALTER/CREATE-INDEX-IF-NOT-EXISTS
    rather than folded into CREATE TABLE — CREATE TABLE IF NOT EXISTS is a no-op on an
    already-existing table (true for any real deployment upgrading from a pre-pgvector
    version), so a column defined only inside it would silently never get added.
    """
    dim = settings.RAGEVAL_EMBEDDING_DIM
    return f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS rageval_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    query TEXT NOT NULL,
    answer TEXT,
    persona TEXT,
    model TEXT,
    relevance REAL,
    groundedness REAL,
    faithfulness REAL,
    cost_usd REAL,
    latency_ms REAL,
    tokens_used INTEGER,
    flags TEXT,
    session_id TEXT,
    needs_review INTEGER DEFAULT 0
);
ALTER TABLE rageval_log ADD COLUMN IF NOT EXISTS query_embedding vector({dim});
CREATE INDEX IF NOT EXISTS idx_rageval_ts ON rageval_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_rageval_review ON rageval_log(needs_review);
CREATE INDEX IF NOT EXISTS idx_rageval_model ON rageval_log(model);
CREATE INDEX IF NOT EXISTS idx_rageval_embedding ON rageval_log
    USING hnsw (query_embedding vector_cosine_ops)
    WHERE query_embedding IS NOT NULL;
"""

def _db_path() -> str:
    """Resolve the SQLite path (live env override, expand ~) and ensure its parent dir exists."""
    path = os.path.expanduser(os.environ.get("RAGEVAL_DB_PATH") or settings.RAGEVAL_DB_PATH)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path

def _execute(sql: str, params: tuple = (), fetchall: bool = False, is_script: bool = False, _retries: int = 3):
    is_pg = bool(settings.POSTGRES_URL)
    conn = None
    cur = None
    try:
        if is_pg:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(settings.POSTGRES_URL)
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            if not is_script:
                sql = sql.replace('?', '%s')
        else:
            conn = sqlite3.connect(_db_path())
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
        if is_script:
            if is_pg:
                cur.execute(sql)
            else:
                cur.executescript(sql)
        else:
            cur.execute(sql, params)
            
        if fetchall:
            res = [dict(r) for r in cur.fetchall()]
        else:
            res = None
        conn.commit()
        return res
    except Exception as e:
        if _retries > 0 and is_pg:
            import psycopg2
            if isinstance(e, psycopg2.OperationalError):
                import time
                time.sleep(0.5)
                return _execute(sql, params, fetchall, is_script, _retries - 1)
        raise e
    finally:
        if cur: cur.close()
        if conn: conn.close()

def init_rageval_table() -> None:
    """Initialize the rageval_log table (idempotent)."""
    global _initialized
    is_pg = bool(settings.POSTGRES_URL)
    _execute(_schema_pg() if is_pg else _SCHEMA_SQLITE, is_script=True)
    log.info("rageval_log initialized (%s)", "postgres" if is_pg else settings.RAGEVAL_DB_PATH)
    _initialized = True


_initialized = False


def _ensure_initialized() -> None:
    """Auto-create the table on first write. Without this, the drop-in @track decorator
    (or any bare `from rageval import log_interaction` use with no api.py and no `rageval
    init` run first) fails on a fresh install with "no such table: rageval_log" — the
    README's whole "pip install, decorate, done" pitch depends on this working with zero
    setup steps."""
    global _initialized
    if not _initialized:
        init_rageval_table()


def _write_interaction_sync(
    query: str,
    answer: str,
    persona: Optional[str],
    scores: Dict[str, Any],
    session_id: Optional[str],
) -> None:
    """Sync helper that does the full log_interaction write in a single thread.

    All sync work is kept in one function so it can be dispatched as a single
    asyncio.to_thread() call from the async log_interaction() below — preventing
    the SQLite commit-visibility issues that arose when two separate to_thread
    dispatches were used for the init check and the execute.
    """
    _ensure_initialized()
    flags = scores.get("flags", [])
    cols = ["timestamp", "query", "answer", "persona", "model",
            "relevance", "groundedness", "faithfulness",
            "cost_usd", "latency_ms", "tokens_used",
            "flags", "session_id", "needs_review"]
    values: tuple = (
        datetime.now(timezone.utc).isoformat(),
        query, answer, persona, scores.get("model"),
        scores.get("relevance"), scores.get("groundedness"), scores.get("faithfulness"),
        scores.get("cost_usd"), scores.get("latency_ms"), scores.get("tokens_used"),
        json.dumps(flags), session_id, int(bool(scores.get("needs_review"))),
    )

    embedding = scores.get("query_embedding") if bool(settings.POSTGRES_URL) else None
    if embedding:
        cols = cols + ["query_embedding"]
        placeholders = ", ".join(["?"] * (len(cols) - 1) + ["?::vector"])
        values = values + ("[" + ",".join(repr(float(x)) for x in embedding) + "]",)
    else:
        placeholders = ", ".join(["?"] * len(cols))

    sql = f"INSERT INTO rageval_log ({', '.join(cols)}) VALUES ({placeholders})"
    _execute(sql, values)


async def log_interaction(
    query: str,
    answer: str,
    persona: Optional[str] = None,
    scores: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> None:
    """Persist a single interaction. On the Postgres tier, also stores the query
    embedding (scores["query_embedding"], a list[float] — see evaluator.score_interaction)
    in the pgvector column when present; SQLite has no such column and this is skipped.

    The blocking psycopg2 I/O (Postgres tier) is offloaded to a worker thread via
    asyncio.to_thread() so the uvicorn event loop stays free during DB writes. All
    sync work is consolidated into one _write_interaction_sync() call to avoid
    commit-visibility races from two separate thread dispatches.
    """
    await asyncio.to_thread(
        _write_interaction_sync,
        query, answer, persona, scores or {}, session_id,
    )

    # OpenTelemetry export — no-op unless RAGEVAL_OTEL_ENDPOINT is configured.
    if init_otel():
        s = scores or {}
        export_span("rag.interaction", {
            "rag.query": query,
            "rag.relevance": s.get("relevance"),
            "rag.groundedness": s.get("groundedness"),
            "rag.cost_usd": s.get("cost_usd"),
            "rag.persona": persona,
        })

def _demo_session_scoping_enabled() -> bool:
    return os.environ.get("DEMO_SESSION_SCOPING", "true").lower() == "true"


def _scope_clause(session_id: Optional[str]) -> tuple[str, tuple]:
    """Session-scoping clause for demo isolation.

    - session_id provided: only rows matching that session (or NULL-session platform rows).
    - session_id=None (admin / platform view): no filter — all rows visible.

    Bug fix: the previous implementation returned
    ``(session_id IS NULL OR session_id = ?, (None,))`` when session_id=None,
    which SQL evaluates as ``session_id IS NULL OR session_id = NULL``. Since
    ``X = NULL`` is always NULL (not TRUE) in SQL, this silently excluded all
    rows that had a real session_id — making all session-scoped interactions
    invisible to platform-level get_metrics() / get_query_log() calls with no
    session_id argument.
    """
    if not _demo_session_scoping_enabled() or session_id is None:
        return "", ()
    return "(session_id IS NULL OR session_id = ?)", (session_id,)


def get_metrics(days: int = 7, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate metrics over the last N days.

    query_volume_by_hour is computed from stored timestamps rather than
    hardcoded to an empty list.
    """
    from datetime import timedelta
    from collections import Counter as _Counter
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    scope_sql, scope_params = _scope_clause(session_id)
    sql = "SELECT * FROM rageval_log WHERE timestamp >= ?"
    params: tuple = (cutoff,)
    if scope_sql:
        sql += f" AND {scope_sql}"
        params += scope_params
    rows = _execute(sql, params, fetchall=True)
    if not rows:
        return {
            "total_queries": 0, "avg_relevance": 0.0, "avg_groundedness": 0.0,
            "avg_faithfulness": 0.0, "avg_latency_ms": 0.0, "total_cost_usd": 0.0,
            "flagged_count": 0, "query_volume_by_hour": [],
        }
    n = len(rows)
    avg = lambda k: sum((r[k] or 0) for r in rows) / n

    # Compute query_volume_by_hour from stored timestamps.
    hour_counts: dict = _Counter()
    for r in rows:
        ts_raw = r.get("timestamp") or ""
        try:
            # ISO format: 2024-01-15T14:32:00+00:00 — extract YYYY-MM-DDTHH
            hour_counts[str(ts_raw)[:13]] += 1
        except Exception:
            pass
    query_volume_by_hour = [
        {"hour": h, "count": c}
        for h, c in sorted(hour_counts.items())
    ]

    return {
        "total_queries": n,
        "avg_relevance": avg("relevance"),
        "avg_groundedness": avg("groundedness"),
        "avg_faithfulness": avg("faithfulness"),
        "avg_latency_ms": avg("latency_ms"),
        "total_cost_usd": sum((r["cost_usd"] or 0) for r in rows),
        "flagged_count": sum(1 for r in rows if r["needs_review"]),
        "query_volume_by_hour": query_volume_by_hour,
    }

def get_query_log(limit: int = 50, needs_review: Optional[bool] = None, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM rageval_log"
    conditions: List[str] = []
    params: tuple = ()
    if needs_review is not None:
        conditions.append("needs_review = ?")
        params = (*params, 1 if needs_review else 0)
    scope_sql, scope_params = _scope_clause(session_id)
    if scope_sql:
        conditions.append(scope_sql)
        params = (*params, *scope_params)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC LIMIT ?"
    params = (*params, limit)
    rows = _execute(sql, params, fetchall=True)
    return rows or []

def get_cost_report(days: int = 30, session_id: Optional[str] = None) -> Dict[str, Any]:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    is_pg = bool(settings.POSTGRES_URL)
    date_expr = "DATE(timestamp)" if is_pg else "date(timestamp)"
    scope_sql, scope_params = _scope_clause(session_id)
    sql = f"""
        SELECT {date_expr} AS day, model, SUM(cost_usd) AS cost
        FROM rageval_log WHERE timestamp >= ? {"AND " + scope_sql if scope_sql else ""}
        GROUP BY day, model
    """
    rows = _execute(sql, (cutoff, *scope_params), fetchall=True)
    daily: Dict[str, float] = {}
    by_model: Dict[str, float] = {}
    total = 0.0
    for r in (rows or []):
        d = str(r["day"]); m = r["model"] or "unknown"; cost = r["cost"] or 0
        daily[d] = daily.get(d, 0) + cost
        by_model[m] = by_model.get(m, 0) + cost
        total += cost
    return {"daily_costs": daily, "by_model": by_model, "total_cost_usd": total, "days": days}
