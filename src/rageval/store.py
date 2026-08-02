"""
RAGeval store — SQLite default, Postgres+pgvector optional.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rageval._compat import settings, get_logger  # self-contained (works when pip-installed)

log = get_logger(__name__)

_SQLITE_SCHEMA = """
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

_POSTGRES_SCHEMA = """
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
    needs_review INTEGER DEFAULT 0,
    query_vector vector
);
CREATE INDEX IF NOT EXISTS idx_rageval_ts ON rageval_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_rageval_review ON rageval_log(needs_review);
CREATE INDEX IF NOT EXISTS idx_rageval_model ON rageval_log(model);
"""


def _db_path() -> str:
    """Resolve the SQLite path (live env override, expand ~) and ensure its parent dir exists."""
    path = os.path.expanduser(os.environ.get("RAGEVAL_DB_PATH") or settings.RAGEVAL_DB_PATH)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


_pool = None
_pool_lock = None


def _init_pool():
    global _pool, _pool_lock
    if _pool is not None:
        return _pool
    import threading
    if _pool_lock is None:
        _pool_lock = threading.Lock()
    with _pool_lock:
        if _pool is not None:
            return _pool
        try:
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
            url = os.getenv("POSTGRES_URL", "").strip()
            if not url:
                _pool = False
                return _pool
            _pool = ConnectionPool(
                url,
                min_size=2,
                max_size=5,
                kwargs={"row_factory": dict_row},
                open=False,
                reconnect_timeout=30,
            )
            # Open the pool in the background
            threading.Thread(target=_pool.open, daemon=True).start()
            log.info("RAGeval Postgres pool initialized")
        except ImportError:
            log.warning("psycopg_pool not installed, using per-call connections")
            _pool = False
        except Exception as e:
            log.warning("Connection pool init failed: %s", e)
            _pool = False
    return _pool


def _get_conn():
    store = os.getenv("RAGEVAL_STORE", "sqlite").strip().lower()
    if store == "postgres":
        url = os.getenv("POSTGRES_URL", "").strip()
        if not url:
            raise ValueError("RAGEVAL_STORE is postgres but POSTGRES_URL is not set")
        pool = _init_pool()
        if pool and pool is not False:
            class ConnWrapper:
                def __init__(self, p):
                    self._p = p
                    self._c = p.getconn(timeout=10)
                def __getattr__(self, item):
                    return getattr(self._c, item)
                def close(self):
                    self._p.putconn(self._c)
                def __enter__(self):
                    return self._c.__enter__()
                def __exit__(self, exc_type, exc_val, exc_tb):
                    res = self._c.__exit__(exc_type, exc_val, exc_tb)
                    self.close()
                    return res
            return ConnWrapper(pool)
        else:
            import psycopg
            from psycopg.rows import dict_row
            return psycopg.connect(url, row_factory=dict_row)
    else:
        # SQLite connection
        c = sqlite3.connect(_db_path())
        c.row_factory = sqlite3.Row
        return c


def init_rageval_table() -> None:
    """Initialize the rageval_log table (idempotent)."""
    store = os.getenv("RAGEVAL_STORE", "sqlite").strip().lower()
    if store == "postgres":
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    conn.commit()
                    has_vector = True
                except Exception:
                    conn.rollback()
                    log.warning("pgvector extension not available on this Postgres instance. Storing without query_vector.")
                    has_vector = False
                
                schema = _POSTGRES_SCHEMA if has_vector else _POSTGRES_SCHEMA.replace(",\n    query_vector vector", "")
                for stmt in schema.split(";"):
                    if stmt.strip():
                        cur.execute(stmt)
                conn.commit()
        finally:
            conn.close()
        log.info("rageval_log initialized in Postgres")
    else:
        with _get_conn() as c:
            c.executescript(_SQLITE_SCHEMA)
        log.info("rageval_log initialized at %s", settings.RAGEVAL_DB_PATH)


async def log_interaction(
    query: str,
    answer: str,
    persona: Optional[str] = None,
    scores: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> None:
    """Persist a single interaction."""
    scores = scores or {}
    flags = scores.get("flags", [])
    store = os.getenv("RAGEVAL_STORE", "sqlite").strip().lower()

    if store == "postgres":
        query_vector = None
        try:
            # Dynamically compute query vector if pgvector is enabled
            import sys
            _svc_dir = os.path.join(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))), "services")
            if _svc_dir not in sys.path:
                sys.path.insert(0, _svc_dir)
            from inference_adapter import embed
            vecs = embed([query])
            if vecs:
                query_vector = vecs[0]
        except Exception as e:
            log.debug("Failed to embed query for pgvector storage: %s", e)

        conn = _get_conn()
        try:
            if query_vector is not None:
                try:
                    from pgvector.psycopg import register_vector
                    register_vector(conn)
                except Exception:
                    pass

            with conn.cursor() as cur:
                has_vector_col = False
                if query_vector is not None:
                    try:
                        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='rageval_log' AND column_name='query_vector'")
                        has_vector_col = bool(cur.fetchone())
                    except Exception:
                        pass

                if query_vector is not None and has_vector_col:
                    cur.execute(
                        """
                        INSERT INTO rageval_log
                          (timestamp, query, answer, persona, model,
                           relevance, groundedness, faithfulness,
                           cost_usd, latency_ms, tokens_used,
                           flags, session_id, needs_review, query_vector)
                        VALUES (%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s, %s,%s,%s, %s)
                        """,
                        (
                            datetime.now(timezone.utc),
                            query, answer, persona, scores.get("model"),
                            scores.get("relevance"), scores.get("groundedness"), scores.get("faithfulness"),
                            scores.get("cost_usd"), scores.get("latency_ms"), scores.get("tokens_used"),
                            json.dumps(flags), session_id, int(bool(scores.get("needs_review"))),
                            query_vector
                        )
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO rageval_log
                          (timestamp, query, answer, persona, model,
                           relevance, groundedness, faithfulness,
                           cost_usd, latency_ms, tokens_used,
                           flags, session_id, needs_review)
                        VALUES (%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s, %s,%s,%s)
                        """,
                        (
                            datetime.now(timezone.utc),
                            query, answer, persona, scores.get("model"),
                            scores.get("relevance"), scores.get("groundedness"), scores.get("faithfulness"),
                            scores.get("cost_usd"), scores.get("latency_ms"), scores.get("tokens_used"),
                            json.dumps(flags), session_id, int(bool(scores.get("needs_review")))
                        )
                    )
            conn.commit()
        finally:
            conn.close()
    else:
        with _get_conn() as c:
            c.execute(
                """
                INSERT INTO rageval_log
                  (timestamp, query, answer, persona, model,
                   relevance, groundedness, faithfulness,
                   cost_usd, latency_ms, tokens_used,
                   flags, session_id, needs_review)
                VALUES (?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    query, answer, persona, scores.get("model"),
                    scores.get("relevance"), scores.get("groundedness"), scores.get("faithfulness"),
                    scores.get("cost_usd"), scores.get("latency_ms"), scores.get("tokens_used"),
                    json.dumps(flags), session_id, int(bool(scores.get("needs_review"))),
                ),
            )


def get_metrics(days: int = 7) -> Dict[str, Any]:
    """Aggregate metrics over the last N days."""
    store = os.getenv("RAGEVAL_STORE", "sqlite").strip().lower()
    if store == "postgres":
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT relevance, groundedness, faithfulness, cost_usd, latency_ms, needs_review "
                    "FROM rageval_log WHERE timestamp >= NOW() - CAST(%s || ' day' AS INTERVAL)",
                    (str(days),)
                )
                rows = cur.fetchall()
        finally:
            conn.close()
    else:
        with _get_conn() as c:
            rows = c.execute(
                "SELECT relevance, groundedness, faithfulness, cost_usd, latency_ms, needs_review "
                "FROM rageval_log WHERE timestamp >= datetime('now', ?)",
                (f"-{days} day",),
            ).fetchall()

    if not rows:
        return {
            "total_queries": 0, "avg_relevance": 0.0, "avg_groundedness": 0.0,
            "avg_faithfulness": 0.0, "avg_latency_ms": 0.0, "total_cost_usd": 0.0,
            "flagged_count": 0, "query_volume_by_hour": [],
        }
    n = len(rows)

    def val(r, k):
        if isinstance(r, dict):
            return r.get(k)
        try:
            return r[k]
        except Exception:
            return None

    avg = lambda k: sum((val(r, k) or 0) for r in rows) / n
    return {
        "total_queries": n,
        "avg_relevance": avg("relevance"),
        "avg_groundedness": avg("groundedness"),
        "avg_faithfulness": avg("faithfulness"),
        "avg_latency_ms": avg("latency_ms"),
        "total_cost_usd": sum((val(r, "cost_usd") or 0) for r in rows),
        "flagged_count": sum(1 for r in rows if val(r, "needs_review")),
        "query_volume_by_hour": [],
    }


def get_query_log(limit: int = 50, needs_review: Optional[bool] = None) -> List[Dict[str, Any]]:
    store = os.getenv("RAGEVAL_STORE", "sqlite").strip().lower()
    sql = "SELECT id, timestamp, query, answer, persona, model, relevance, groundedness, faithfulness, cost_usd, latency_ms, tokens_used, flags, session_id, needs_review FROM rageval_log"
    params: tuple = ()
    if needs_review is not None:
        sql += " WHERE needs_review = %s" if store == "postgres" else " WHERE needs_review = ?"
        params = (1 if needs_review else 0,)
    sql += " ORDER BY id DESC LIMIT " + ("%s" if store == "postgres" else "?")
    params = (*params, limit)

    if store == "postgres":
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        finally:
            conn.close()
        out = []
        for r in rows:
            rd = dict(r)
            if isinstance(rd.get("timestamp"), datetime):
                rd["timestamp"] = rd["timestamp"].isoformat()
            if isinstance(rd.get("flags"), str):
                try:
                    rd["flags"] = json.loads(rd["flags"])
                except Exception:
                    pass
            out.append(rd)
        return out
    else:
        with _get_conn() as c:
            rows = c.execute(sql, params).fetchall()
        out = []
        for r in rows:
            rd = dict(r)
            if isinstance(rd.get("flags"), str):
                try:
                    rd["flags"] = json.loads(rd["flags"])
                except Exception:
                    pass
            out.append(rd)
        return out


def get_cost_report(days: int = 30) -> Dict[str, Any]:
    store = os.getenv("RAGEVAL_STORE", "sqlite").strip().lower()
    if store == "postgres":
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DATE(timestamp) AS day, model, SUM(cost_usd) AS cost "
                    "FROM rageval_log WHERE timestamp >= NOW() - CAST(%s || ' day' AS INTERVAL) "
                    "GROUP BY day, model",
                    (str(days),)
                )
                rows = cur.fetchall()
        finally:
            conn.close()
    else:
        with _get_conn() as c:
            rows = c.execute(
                "SELECT date(timestamp) AS day, model, SUM(cost_usd) AS cost "
                "FROM rageval_log WHERE timestamp >= datetime('now', ?) "
                "GROUP BY day, model",
                (f"-{days} day",),
            ).fetchall()
    daily: Dict[str, float] = {}
    by_model: Dict[str, float] = {}
    total = 0.0
    for r in rows:
        d = str(r["day"])
        m = r["model"] or "unknown"
        cost = float(r["cost"] or 0)
        daily[d] = daily.get(d, 0) + cost
        by_model[m] = by_model.get(m, 0) + cost
        total += cost
    return {"daily_costs": daily, "by_model": by_model, "total_cost_usd": total, "days": days}
