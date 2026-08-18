"""RAGeval API tests — offline (health, routes, metrics read SQLite)."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _client():
    from api import app
    return TestClient(app)


def _internal_auth_headers() -> dict:
    """The internal-token middleware gates POST write routes only — /, /health, /docs,
    static assets, all GET /eval/* routes, and the /eval/live websocket stay open —
    when REQUIRE_INTERNAL_TOKEN=true (opt-in, off by default: the public dashboard
    itself needs to be reachable with no token). Reuse whatever real token is
    configured in the environment so tests exercise the actual endpoint, not just the
    pass-through/403 behavior of the gate."""
    token = os.environ.get("RAGEVAL_INTERNAL_TOKEN", "")
    return {"X-RAGeval-Internal-Token": token} if token else {}


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200 and r.json()["service"] == "rageval"


def test_routes_registered():
    from api import app
    paths = {r.path for r in app.routes}
    for p in ("/eval/log", "/eval/score", "/eval/metrics", "/eval/queries",
              "/eval/cost-report", "/eval/alerts", "/eval/retrieval-bench",
              "/eval/embedding-comparison"):
        assert p in paths, p


def test_metrics_reads_offline():
    r = _client().get("/eval/metrics?days=7", headers=_internal_auth_headers())
    assert r.status_code in (200, 401, 403) and (r.status_code != 200 or isinstance(r.json(), dict))


def test_api_compat_shim_copies_postgres_url_once(tmp_path):
    """api.py's own startup shim (POSTGRES_URL -> RAGEVAL_POSTGRES_URL when the latter
    isn't set) is scoped to this standalone app's process only — verified in a real
    subprocess since api.py has almost certainly already been imported earlier in this
    test session, and Python won't re-run a cached module's top-level code on a second
    `import api`, which would make an in-process test of this meaningless."""
    import subprocess
    env = {
        **os.environ,
        "RAGEVAL_POSTGRES_URL": "",
        "POSTGRES_URL": "postgresql://compat-shim-test/db",
        "RAGEVAL_DB_PATH": str(tmp_path / "shim_test.db"),
        "TELEMETRY_OPT_OUT": "true",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True",
    }
    result = subprocess.run(
        [sys.executable, "-c",
         "import api; import os; print('RAGEVAL_POSTGRES_URL=' + os.environ.get('RAGEVAL_POSTGRES_URL', ''))"],
        cwd=str(Path(__file__).resolve().parent.parent), env=env, capture_output=True, text=True, timeout=60,
    )
    assert "RAGEVAL_POSTGRES_URL=postgresql://compat-shim-test/db" in result.stdout, result.stderr


def test_eval_score_returns_503_when_insufficient_judges(monkeypatch):
    """The InsufficientJudgesError -> HTTP 503 wiring, exercised through the real
    FastAPI request stack (middleware included), not just at the evaluator level.

    Patches rageval.evaluator.settings (the actual object the evaluator reads at
    call time) rather than rageval._compat.settings, which may be a different
    object after importlib.reload() in the sqlite_store fixture.
    """
    import rageval.evaluator as ev_mod
    # Patch the settings object that evaluator.py actually imported.
    monkeypatch.setattr(ev_mod.settings, "JUDGE_MODELS", ["anthropic/claude-haiku-4-5"])
    r = _client().post(
        "/eval/score",
        json={"query": "q", "answer": "a", "chunks": ["c"]},
        headers=_internal_auth_headers(),
    )
    if r.status_code in (401, 403):
        import pytest
        pytest.skip("no valid RAGEVAL_INTERNAL_TOKEN in this environment")
    assert r.status_code == 503, f"Expected 503, got {r.status_code}: {r.text[:200]}"
    assert "judge" in r.json()["detail"].lower()


# ─── GET routes stay open to the browser regardless of the token gate ─────────

def test_get_eval_routes_accessible_without_internal_token(monkeypatch):
    """GET /eval/* endpoints must NOT be blocked by the middleware even when
    REQUIRE_INTERNAL_TOKEN=true. These routes feed the browser dashboard — any
    403 here means the entire UI shows empty data.

    Regression coverage: /eval/metrics, /eval/queries, /eval/alerts, /eval/config,
    /eval/events, /eval/cost-report must all pass through GET requests regardless
    of the token.
    """
    import pytest
    monkeypatch.setenv("REQUIRE_INTERNAL_TOKEN", "true")
    monkeypatch.setenv("RAGEVAL_INTERNAL_TOKEN", "secret-sentinel-value")
    # Reload api so the middleware picks up the new env values.
    import importlib
    import api as api_mod
    importlib.reload(api_mod)
    client = TestClient(api_mod.app, raise_server_exceptions=False)

    get_routes = [
        "/eval/metrics?days=7",
        "/eval/queries?limit=5",
        "/eval/alerts",
        "/eval/config",
        "/eval/events",
        "/eval/cost-report?days=7",
    ]
    for route in get_routes:
        r = client.get(route)  # No X-RAGeval-Internal-Token header.
        assert r.status_code != 403, (
            f"{route} returned 403 to a browser GET with no token. "
            "Dashboard will show empty data in production."
        )


def test_post_eval_blocked_without_internal_token(monkeypatch):
    """POST /eval/score and POST /eval/log must still require the token
    when REQUIRE_INTERNAL_TOKEN=true — only GETs are open to the browser."""
    monkeypatch.setenv("REQUIRE_INTERNAL_TOKEN", "true")
    monkeypatch.setenv("RAGEVAL_INTERNAL_TOKEN", "secret-sentinel-value")
    import importlib
    import api as api_mod
    importlib.reload(api_mod)
    client = TestClient(api_mod.app, raise_server_exceptions=False)

    r = client.post(
        "/eval/score",
        json={"query": "q", "answer": "a", "chunks": ["c"]},
        # Deliberately no X-RAGeval-Internal-Token header.
    )
    assert r.status_code == 403, (
        "POST /eval/score should be blocked by token gate when REQUIRE_INTERNAL_TOKEN=true. "
        f"Got {r.status_code}."
    )


# ─── No /api/v1/auth bypass ────────────────────────────────────────────────────

def test_no_api_v1_auth_bypass_in_routes():
    """The middleware's old /api/v1/auth/ exemption was dead code — RAGeval has no
    routes there — and has been removed. Verify the app has no routes registered
    under /api/v1/ either."""
    from api import app
    paths = {r.path for r in app.routes}
    api_v1_routes = [p for p in paths if p.startswith("/api/v1/")]
    assert not api_v1_routes, (
        f"Unexpected /api/v1/ routes found: {api_v1_routes}. "
        "These would be silently auth-bypassed if the /api/v1/auth/ middleware exemption "
        "is ever re-added."
    )


# ─── /eval/retrieval-bench: precision@k / recall@k / MRR with ground truth ─────

def test_retrieval_bench_without_ground_truth_returns_relevance_only():
    """No relevant_chunks supplied: only the label-free embedding-relevance score is
    returned, ranking metrics are omitted rather than silently zeroed."""
    r = _client().post(
        "/eval/retrieval-bench",
        json={
            "queries": ["What is ARR?"],
            "chunks_a": [["Annual Recurring Revenue is a SaaS metric."]],
            "chunks_b": [["The weather today is sunny."]],
        },
        headers=_internal_auth_headers(),
    )
    if r.status_code in (401, 403):
        pytest.skip("no valid RAGEVAL_INTERNAL_TOKEN in this environment")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_ground_truth"] is False
    assert "mean_relevance" in body["strategy_a"]
    assert "precision_at_k" not in body["strategy_a"]


def test_retrieval_bench_with_ground_truth_returns_ranking_metrics():
    """relevant_chunks supplied: precision@k/recall@k/MRR are computed per strategy and
    the winner is decided by ranking quality (F1 of precision/recall), not embedding
    similarity — strategy A retrieves the labeled-relevant chunk first, strategy B never
    retrieves it at all, so A must win regardless of either chunk's topical similarity."""
    r = _client().post(
        "/eval/retrieval-bench",
        json={
            "queries": ["What is ARR?"],
            "chunks_a": [["Annual Recurring Revenue is a SaaS metric.", "unrelated filler"]],
            "chunks_b": [["completely unrelated chunk one", "completely unrelated chunk two"]],
            "relevant_chunks": [["Annual Recurring Revenue is a SaaS metric."]],
            "precision_k": 1,
            "recall_k": 2,
        },
        headers=_internal_auth_headers(),
    )
    if r.status_code in (401, 403):
        pytest.skip("no valid RAGEVAL_INTERNAL_TOKEN in this environment")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_ground_truth"] is True
    assert body["strategy_a"]["precision_at_k"] == pytest.approx(1.0)
    assert body["strategy_a"]["mrr"] == pytest.approx(1.0)
    assert body["strategy_b"]["precision_at_k"] == pytest.approx(0.0)
    assert body["winner"] == "a"


def test_retrieval_bench_relevant_chunks_length_mismatch_is_400():
    r = _client().post(
        "/eval/retrieval-bench",
        json={
            "queries": ["q1", "q2"],
            "chunks_a": [["a"], ["a"]],
            "chunks_b": [["b"], ["b"]],
            "relevant_chunks": [["a"]],  # only 1 entry for 2 queries
        },
        headers=_internal_auth_headers(),
    )
    if r.status_code in (401, 403):
        pytest.skip("no valid RAGEVAL_INTERNAL_TOKEN in this environment")
    assert r.status_code == 400

