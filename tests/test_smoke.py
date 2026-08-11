"""Smoke tests for RAGeval."""
import importlib
import os
import tempfile
import pytest


def test_rageval_postgres_url_is_read(monkeypatch):
    monkeypatch.setenv("RAGEVAL_POSTGRES_URL", "postgresql://ragevals-own-db/x")
    import core.config as app_config
    importlib.reload(app_config)
    assert app_config.settings.POSTGRES_URL == "postgresql://ragevals-own-db/x"


def test_generic_postgres_url_is_never_read_by_the_library_settings(monkeypatch):
    """core.config / rageval._compat must NOT fall back to a bare POSTGRES_URL — that
    fallback used to exist and it made rageval, imported as a library, silently adopt a
    host app's own unrelated database whenever that host (reasonably) also used the
    generic POSTGRES_URL name for itself. Confirmed live: this exact fallback wrote
    rageval's schema into another real project's production Postgres. The only place
    POSTGRES_URL is still honored is api.py's own narrow startup shim (see
    test_api.py) — never in these shared settings modules.

    Uses an explicit empty string, not delenv: core/config.py calls load_dotenv() fresh
    on every reload, and load_dotenv()'s default override=False only skips keys that are
    already *present* — a deleted key looks absent and gets silently refilled from the
    real .env on the next reload (this is the exact mechanism that leaked a real
    credential into a test failure once already; don't repeat it)."""
    monkeypatch.setenv("RAGEVAL_POSTGRES_URL", "")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://some-other-apps-unrelated-db/z")
    import core.config as app_config
    importlib.reload(app_config)
    assert app_config.settings.POSTGRES_URL == ""

    import sys
    sys.path.insert(0, "src")
    import rageval._compat as compat
    importlib.reload(compat)
    assert compat.settings.POSTGRES_URL == ""


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
