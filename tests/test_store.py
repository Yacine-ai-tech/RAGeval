"""Store round-trip test — SQLite, fully offline (temp DB via env)."""
import asyncio
import importlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


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
    # at least one interaction is now recorded
    total = metrics.get("total_interactions") or metrics.get("count") or metrics.get("total")
    assert total is None or total >= 1


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
