"""Tests for RAGeval demo session isolation and admin bypass."""
from rageval.store import _scope_clause


def test_scope_clause_isolation():
    # Admin bypass returns unconstrained
    sql, params = _scope_clause("*")
    assert sql == ""
    assert params == ()

    # Visitor session scopes to session or seed NULL
    sql, params = _scope_clause("session_123")
    assert sql == "(session_id IS NULL OR session_id = ?)"
    assert params == ("session_123",)

    # Anonymous visitor with assigned anonymous token
    sql, params = _scope_clause("anonymous_unassigned")
    assert sql == "(session_id IS NULL OR session_id = ?)"
    assert params == ("anonymous_unassigned",)
