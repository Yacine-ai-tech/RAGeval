"""RAGeval API tests — offline (health, routes, metrics read SQLite)."""
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _client():
    from api import app
    return TestClient(app)


def _internal_auth_headers() -> dict:
    """The internal-token middleware gates every route except /, /health, /docs, static
    assets, and /api/v1/auth/* when REQUIRE_INTERNAL_TOKEN=true (opt-in, off by default —
    the public dashboard itself needs to be reachable with no token). Reuse whatever real
    token is configured in the environment so tests exercise the actual endpoint, not
    just the pass-through/403 behavior of the gate."""
    token = os.environ.get("OMNIINTEL_INTERNAL_TOKEN", "")
    return {"X-OmniIntel-Internal-Token": token} if token else {}


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
    }
    result = subprocess.run(
        [sys.executable, "-c",
         "import api; import os; print('RAGEVAL_POSTGRES_URL=' + os.environ.get('RAGEVAL_POSTGRES_URL', ''))"],
        cwd=str(Path(__file__).resolve().parent.parent), env=env, capture_output=True, text=True, timeout=30,
    )
    assert "RAGEVAL_POSTGRES_URL=postgresql://compat-shim-test/db" in result.stdout, result.stderr


def test_eval_score_returns_503_when_insufficient_judges(monkeypatch):
    """The InsufficientJudgesError -> HTTP 503 wiring, exercised through the real
    FastAPI request stack (middleware included), not just at the evaluator level."""
    from rageval._compat import settings
    monkeypatch.setattr(settings, "JUDGE_MODELS", ["anthropic/claude-haiku-4-5"])
    r = _client().post(
        "/eval/score",
        json={"query": "q", "answer": "a", "chunks": ["c"]},
        headers=_internal_auth_headers(),
    )
    if r.status_code in (401, 403):
        import pytest
        pytest.skip("no valid OMNIINTEL_INTERNAL_TOKEN in this environment")
    assert r.status_code == 503
    assert "judge" in r.json()["detail"].lower()
