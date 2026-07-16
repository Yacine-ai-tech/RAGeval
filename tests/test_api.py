"""RAGeval API tests — offline (health, routes, metrics read SQLite)."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _client():
    from api import app
    return TestClient(app)


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
    r = _client().get("/eval/metrics?days=7")
    assert r.status_code in (200, 401, 403) and (r.status_code != 200 or isinstance(r.json(), dict))
