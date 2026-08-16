"""Shared test fixtures.

Ensures any test asserting SQLite-only, offline behavior actually gets an
isolated SQLite DB — not the real Postgres from the environment/.env.
`rageval._compat.settings` (used by store.py/evaluator.py) and `core.config.settings`
are two *independent* readers of the same env vars; reloading only one of them
(a mistake this suite made before) leaves the other still holding a live Postgres
connection string, so "offline" tests silently write to production instead of a
temp file.

Blanks only RAGEVAL_POSTGRES_URL, RAGeval's own dedicated var — never the generic
POSTGRES_URL, which may belong to an unrelated database also configured in this
environment. See core/config.py / rageval/_compat.py for why RAGEVAL_POSTGRES_URL
takes priority.
"""
from __future__ import annotations

import importlib
import tempfile

import pytest


@pytest.fixture
def sqlite_store(monkeypatch):
    """Yields the freshly-reloaded `rageval.store` module, pointed at a throwaway
    temp SQLite DB with RAGEVAL_POSTGRES_URL forced empty — genuinely offline
    regardless of what the real environment/.env has configured."""
    monkeypatch.setenv("RAGEVAL_DB_PATH", tempfile.mktemp(suffix="_rageval_test.db"))
    monkeypatch.setenv("RAGEVAL_POSTGRES_URL", "")

    import core.config as app_config
    importlib.reload(app_config)
    import rageval._compat as compat
    importlib.reload(compat)
    import rageval.store as store
    importlib.reload(store)

    store.init_rageval_table()
    yield store
