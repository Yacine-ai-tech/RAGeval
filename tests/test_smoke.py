"""Smoke tests for RAGeval."""
import os
import tempfile
import pytest


def test_package_imports():
    import rageval
    assert rageval.__version__


def test_evaluator_instantiates():
    from rageval.evaluator import RAGEvaluator
    ev = RAGEvaluator()
    assert ev is not None


def test_cost_calculation():
    from rageval.evaluator import RAGEvaluator
    cost = RAGEvaluator.calculate_cost(tokens=1000, model="groq/llama-3.3-70b-versatile")
    assert cost >= 0


def test_store_init_idempotent(tmp_path, monkeypatch):
    db = tmp_path / "rageval.db"
    monkeypatch.setenv("RAGEVAL_DB_PATH", str(db))
    # Re-import settings to pick up the patched env
    import importlib
    from core import config
    importlib.reload(config)
    from rageval.store import init_rageval_table
    init_rageval_table()
    init_rageval_table()  # idempotent
    assert db.exists()


def test_app_creates():
    from api import app
    assert app.title == "RAGeval"


def test_decorator_wraps_function():
    from rageval.decorator import track

    @track(model="groq/llama-3.3-70b-versatile")
    def fn(query: str):
        return "stub answer"

    assert callable(fn)
