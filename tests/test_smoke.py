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


def test_store_init_idempotent(sqlite_store):
    sqlite_store.init_rageval_table()  # idempotent — already called once by the fixture
    import os
    assert os.path.exists(sqlite_store._db_path())


def test_app_creates():
    from api import app
    assert app.title == "RAGeval"


def test_decorator_wraps_function():
    from rageval.decorator import track

    @track(model="groq/llama-3.3-70b-versatile")
    def fn(query: str):
        return "stub answer"

    assert callable(fn)
