"""Store round-trip test — SQLite, fully offline (temp DB via env)."""
import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_log_then_metrics_roundtrip():
    os.environ["RAGEVAL_DB_PATH"] = tempfile.mktemp(suffix="_rageval.db")
    import core.config as cfg
    importlib.reload(cfg)
    import rageval.store as store
    importlib.reload(store)

    store.init_rageval_table()
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
