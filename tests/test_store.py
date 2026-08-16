"""Store round-trip test — SQLite, fully offline (temp DB via env).

DEFECT-12 fix: test_log_then_metrics_roundtrip previously checked for keys
'total_interactions', 'count', or 'total' — none of which exist in get_metrics().
The actual key is 'total_queries'. The old assertion was always True (None is None)
and never validated that the interaction was actually persisted.
"""
import asyncio
import importlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def test_log_then_metrics_roundtrip(sqlite_store):
    store = sqlite_store
    scores = {
        "relevance": 0.7, "groundedness": 0.8, "faithfulness": 0.7,
        "overall_quality": 0.75, "cost_usd": 0.0012, "latency_ms": 120.0,
        "tokens_used": 50, "model": "groq/llama-3.3-70b-versatile",
        "flags": [], "needs_review": False,
    }
    asyncio.run(store.log_interaction("What is ARR?", "Annual Recurring Revenue.",
                                      "cfo", scores, "sess-1"))
    metrics = store.get_metrics(days=1)
    assert isinstance(metrics, dict)

    # DEFECT-12 fix: assert on the actual key name 'total_queries'.
    # Old code used 'total_interactions'/'count'/'total' — all missing — so
    # total was always None and `assert None is None` passed vacuously even
    # when log_interaction() silently failed.
    total = metrics.get("total_queries")
    assert total is not None, (
        "get_metrics() did not return 'total_queries' — check store.get_metrics() key names. "
        f"Got keys: {list(metrics.keys())}"
    )
    assert total >= 1, f"Expected at least 1 interaction, got {total}"


def test_metrics_avg_relevance_correct(sqlite_store):
    """Verify that avg_relevance is computed from logged data, not hardcoded."""
    store = sqlite_store
    scores = {
        "relevance": 0.6, "groundedness": 0.5, "faithfulness": 0.55,
        "overall_quality": 0.55, "cost_usd": 0.001, "latency_ms": 100.0,
        "tokens_used": 30, "model": "groq/llama-3.3-70b-versatile",
        "flags": [], "needs_review": False,
    }
    asyncio.run(store.log_interaction("Test query", "Test answer", None, scores, None))
    metrics = store.get_metrics(days=1)
    assert metrics["avg_relevance"] == pytest.approx(0.6, abs=0.01)
    assert metrics["total_cost_usd"] == pytest.approx(0.001, abs=1e-6)


def test_query_volume_by_hour_is_populated(sqlite_store):
    """DEFECT-17 regression: query_volume_by_hour must not be hardcoded to []."""
    store = sqlite_store
    scores = {
        "relevance": 0.7, "groundedness": 0.7, "faithfulness": 0.7,
        "overall_quality": 0.7, "cost_usd": 0.001, "latency_ms": 50.0,
        "tokens_used": 20, "model": "groq/llama-3.3-70b-versatile",
        "flags": [], "needs_review": False,
    }
    asyncio.run(store.log_interaction("hourly query", "answer", None, scores, None))
    metrics = store.get_metrics(days=1)
    vol = metrics.get("query_volume_by_hour")
    assert vol is not None, "query_volume_by_hour key missing from get_metrics() response"
    assert isinstance(vol, list), f"Expected list, got {type(vol)}"
    assert len(vol) >= 1, "Expected at least one entry in query_volume_by_hour after logging"
    # Each entry must have 'hour' and 'count' keys.
    entry = vol[0]
    assert "hour" in entry and "count" in entry, f"Unexpected entry shape: {entry}"


def test_log_interaction_auto_initializes_table(monkeypatch):
    """The drop-in @track decorator (or any bare `from rageval import log_interaction`
    use with no api.py and no `rageval init` run first) must work with zero setup — this
    is the entire premise of the README's "pip install, decorate, done" pitch. Deliberately
    does NOT call init_rageval_table() first, unlike the sqlite_store fixture."""
    monkeypatch.setenv("RAGEVAL_DB_PATH", tempfile.mktemp(suffix="_rageval_uninitialized.db"))
    monkeypatch.setenv("RAGEVAL_POSTGRES_URL", "")

    import core.config as app_config
    importlib.reload(app_config)
    import rageval._compat as compat
    importlib.reload(compat)
    import rageval.store as store
    importlib.reload(store)  # resets store._initialized to False

    asyncio.run(store.log_interaction("fresh install", "answer", None, {"relevance": 0.5}, None))

    rows = store.get_query_log(limit=10)
    assert any(r["query"] == "fresh install" for r in rows)


def test_get_metrics_flagged_count(sqlite_store):
    """flagged_count must reflect actual needs_review=1 rows."""
    store = sqlite_store
    flagged_scores = {
        "relevance": 0.2, "groundedness": 0.3, "faithfulness": 0.2,
        "overall_quality": 0.25, "cost_usd": 0.002, "latency_ms": 6000.0,
        "tokens_used": 100, "model": "groq/llama-3.3-70b-versatile",
        "flags": ["LOW_RETRIEVAL_RELEVANCE", "HIGH_LATENCY"], "needs_review": True,
    }
    asyncio.run(store.log_interaction("bad query", "bad answer", None, flagged_scores, None))
    metrics = store.get_metrics(days=1)
    assert metrics["flagged_count"] >= 1
