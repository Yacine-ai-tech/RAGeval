import sqlite3
from types import SimpleNamespace

from rageval import store


def _use_sqlite(path, monkeypatch):
    monkeypatch.setenv("RAGEVAL_DB_PATH", str(path))
    monkeypatch.setattr(
        store,
        "settings",
        SimpleNamespace(POSTGRES_URL="", RAGEVAL_DB_PATH=str(path)),
    )


def test_sqlite_clean_bootstrap_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "clean.db"
    _use_sqlite(db_path, monkeypatch)

    store.init_rageval_table()
    store.init_rageval_table()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(rageval_log)")}
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(rageval_log)")}
    assert "needs_review" in columns
    assert "idx_rageval_review" in indexes


def test_sqlite_bootstrap_migrates_legacy_needs_review_column(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    _use_sqlite(db_path, monkeypatch)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE rageval_log (
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
                session_id TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO rageval_log (timestamp, query) VALUES (?, ?)",
            ("2026-01-01T00:00:00+00:00", "legacy query"),
        )

    store.init_rageval_table()
    store.init_rageval_table()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(rageval_log)")}
        migrated_row = conn.execute(
            "SELECT query, needs_review FROM rageval_log"
        ).fetchone()
    assert "needs_review" in columns
    assert migrated_row == ("legacy query", 0)


def test_postgres_schema_contains_legacy_column_migration(monkeypatch):
    monkeypatch.setattr(
        store,
        "settings",
        SimpleNamespace(POSTGRES_URL="postgresql://test", RAGEVAL_EMBEDDING_DIM=1024),
    )
    assert "ADD COLUMN IF NOT EXISTS needs_review INTEGER DEFAULT 0" in store._schema_pg()
