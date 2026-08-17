"""DSPy telemetry round-trip test — SQLite, fully offline (temp DB via env).

Exercises the real persistence path (log_dspy_run + dspy_compile_callback), not
just an import/compile check — a compilation event should actually land in the
store, the same contract a real dspy.BootstrapFewShot caller would use.
"""
import asyncio
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.mark.unit
def test_log_dspy_run_persists_event(sqlite_store):
    store = sqlite_store
    import rageval.dspy_integration as dspy_integration
    importlib.reload(dspy_integration)

    asyncio.run(dspy_integration.log_dspy_run(
        program_name="business_analysis_pipeline",
        candidates=["few-shot-1", "few-shot-2", "few-shot-3"],
        winner="few-shot-2",
        eval_metric="accuracy",
        eval_score=0.82,
    ))

    rows = store.get_query_log(limit=10)
    assert any(r["query"] == "dspy_compile::business_analysis_pipeline" for r in rows)
    row = next(r for r in rows if r["query"] == "dspy_compile::business_analysis_pipeline")
    assert row["model"] == "dspy:business_analysis_pipeline"
    assert row["relevance"] == pytest.approx(0.82)


@pytest.mark.unit
def test_dspy_compile_callback_wraps_sync_fn_and_logs(sqlite_store):
    store = sqlite_store
    import rageval.dspy_integration as dspy_integration
    importlib.reload(dspy_integration)

    @dspy_integration.dspy_compile_callback
    def compile_program():
        # Stands in for a real `optimizer.compile(program, trainset=...)` call —
        # dspy_compile_callback only needs this return shape, not dspy itself.
        return {
            "program_name": "planner_analyst_reporter",
            "candidates": ["v1", "v2"],
            "winner": "v2",
            "eval_metric": "exact_match",
            "eval_score": 0.91,
        }

    result = compile_program()
    assert result["winner"] == "v2"  # original return value is passed through

    # dspy_compile_callback logs via _fire_and_forget: from this sync/no-running-loop
    # context it hands the coroutine to a background event-loop thread
    # (asyncio.run_coroutine_threadsafe) and returns immediately, so the write can
    # still be in flight the instant compile_program() returns. Poll briefly instead
    # of asserting on the very next line.
    import time
    deadline = time.monotonic() + 2.0
    rows: list = []
    while time.monotonic() < deadline:
        rows = store.get_query_log(limit=10)
        if any(r["query"] == "dspy_compile::planner_analyst_reporter" for r in rows):
            break
        time.sleep(0.02)
    assert any(r["query"] == "dspy_compile::planner_analyst_reporter" for r in rows), (
        f"dspy_compile::planner_analyst_reporter not logged within 2s. Rows: {rows}"
    )


@pytest.mark.unit
def test_dspy_module_compile():
    try:
        import dspy
        class RAG(dspy.Module):
            def __init__(self):
                super().__init__()
                self.generate_answer = dspy.ChainOfThought("context, question -> answer")

            def forward(self, question, context):
                return self.generate_answer(context=context, question=question)

        rag = RAG()
        assert rag is not None
    except ImportError:
        pytest.skip("dspy-ai not installed — optional dependency")
