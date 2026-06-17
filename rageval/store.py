"""
RAGeval store — SQLite default, Postgres+pgvector optional.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rageval._compat import settings, get_logger  # self-contained (works when pip-installed)

log = get_logger(__name__)


_SCHEMA = """
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


def _db_path() -> str:
    """Resolve the SQLite path (live env override, expand ~) and ensure its parent dir exists."""
    path = os.path.expanduser(os.environ.get("RAGEVAL_DB_PATH") or settings.RAGEVAL_DB_PATH)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def _conn() -> sqlite3.Connection:
    """Open a SQLite connection (Postgres support would override here)."""
    c = sqlite3.connect(_db_path())
    c.row_factory = sqlite3.Row
    return c


def init_rageval_table() -> None:
    """Initialize the rageval_log table (idempotent)."""
    with _conn() as c:
        c.executescript(_SCHEMA)
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
    with _conn() as c:
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
                datetime.utcnow().isoformat(),
                query, answer, persona, scores.get("model"),
                scores.get("relevance"), scores.get("groundedness"), scores.get("faithfulness"),
                scores.get("cost_usd"), scores.get("latency_ms"), scores.get("tokens_used"),
                json.dumps(flags), session_id, int(bool(scores.get("needs_review"))),
            ),
        )


def get_metrics(days: int = 7) -> Dict[str, Any]:
    """Aggregate metrics over the last N days."""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM rageval_log WHERE timestamp >= datetime('now', ?)",
            (f"-{days} day",),
        ).fetchall()
    if not rows:
        return {
            "total_queries": 0, "avg_relevance": 0.0, "avg_groundedness": 0.0,
            "avg_faithfulness": 0.0, "avg_latency_ms": 0.0, "total_cost_usd": 0.0,
            "flagged_count": 0, "query_volume_by_hour": [],
        }
    n = len(rows)
    avg = lambda k: sum((r[k] or 0) for r in rows) / n
    return {
        "total_queries": n,
        "avg_relevance": avg("relevance"),
        "avg_groundedness": avg("groundedness"),
        "avg_faithfulness": avg("faithfulness"),
        "avg_latency_ms": avg("latency_ms"),
        "total_cost_usd": sum((r["cost_usd"] or 0) for r in rows),
        "flagged_count": sum(1 for r in rows if r["needs_review"]),
        "query_volume_by_hour": [],
    }


def get_query_log(limit: int = 50, needs_review: Optional[bool] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM rageval_log"
    params: tuple = ()
    if needs_review is not None:
        sql += " WHERE needs_review = ?"
        params = (1 if needs_review else 0,)
    sql += " ORDER BY id DESC LIMIT ?"
    params = (*params, limit)
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_cost_report(days: int = 30) -> Dict[str, Any]:
    with _conn() as c:
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
        d = r["day"]; m = r["model"] or "unknown"; cost = r["cost"] or 0
        daily[d] = daily.get(d, 0) + cost
        by_model[m] = by_model.get(m, 0) + cost
        total += cost
    return {"daily_costs": daily, "by_model": by_model, "total_cost_usd": total, "days": days}
