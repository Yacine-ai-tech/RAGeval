import os
import uuid
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from rageval import store


@pytest.fixture
def postgres_schema(monkeypatch):
    if os.getenv("RUN_POSTGRES_MIGRATION_TESTS") != "true":
        pytest.skip("Postgres migration tests are enabled only in the isolated CI database")
    dsn = os.getenv("TEST_POSTGRES_URL")
    if not dsn:
        pytest.skip("TEST_POSTGRES_URL is not configured")
    if urlsplit(dsn).hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("Migration tests require a loopback-only Postgres database")

    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import make_dsn

    schema = f"rageval_migration_{uuid.uuid4().hex}"
    admin = psycopg2.connect(dsn)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    scoped_dsn = make_dsn(dsn, options=f"-c search_path={schema},public")
    monkeypatch.setattr(
        store,
        "settings",
        SimpleNamespace(
            POSTGRES_URL=scoped_dsn,
            RAGEVAL_EMBEDDING_DIM=1024,
            RAGEVAL_DB_PATH="unused-in-postgres-test",
        ),
    )
    monkeypatch.setattr(store, "_pg_pool", False)
    try:
        yield admin, schema
    finally:
        with admin.cursor() as cur:
            cur.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


def _columns(conn, schema):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'rageval_log'",
            (schema,),
        )
        return {row[0] for row in cur.fetchall()}


def test_postgres_clean_bootstrap_is_idempotent(postgres_schema):
    admin, schema = postgres_schema

    store.init_rageval_table()
    store.init_rageval_table()

    assert {"needs_review", "query_embedding"} <= _columns(admin, schema)


def test_postgres_legacy_schema_migrates_without_data_loss(postgres_schema):
    admin, schema = postgres_schema
    with admin.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE {schema}.rageval_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
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
        cur.execute(
            f"INSERT INTO {schema}.rageval_log (timestamp, query) VALUES (NOW(), %s)",
            ("legacy query",),
        )

    store.init_rageval_table()
    store.init_rageval_table()

    assert {"needs_review", "query_embedding"} <= _columns(admin, schema)
    with admin.cursor() as cur:
        cur.execute(f"SELECT query, needs_review FROM {schema}.rageval_log")
        assert cur.fetchone() == ("legacy query", 0)


def test_postgres_migration_error_rolls_back_bootstrap(postgres_schema, monkeypatch):
    admin, schema = postgres_schema
    monkeypatch.setattr(store.settings, "RAGEVAL_EMBEDDING_DIM", 0)
    with pytest.raises(Exception):
        store.init_rageval_table()
    with admin.cursor() as cur:
        cur.execute(
            "SELECT to_regclass(%s)",
            (f"{schema}.rageval_log",),
        )
        assert cur.fetchone()[0] is None
