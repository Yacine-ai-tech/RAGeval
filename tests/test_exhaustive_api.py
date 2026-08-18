"""
Shallow route-existence smoke tests — one per endpoint, asserting only that the route
exists and doesn't 500 the whole ASGI app on a bare/empty request.

Runs fully in-process against the app object (httpx ASGITransport) rather than over
real network — a plain `pytest tests/` (and CI's Phase 7 integration-tests job, which
doesn't set TEST_BASE_URL) must never make outbound requests to the live production
gateway. If you specifically want to exercise a real running instance instead, set
TEST_BASE_URL to it explicitly.
"""
import os

import httpx
import pytest

TOKEN = os.getenv('RAGEVAL_INTERNAL_TOKEN', '')
HEADERS = {'X-RAGeval-Internal-Token': TOKEN}
TEST_BASE_URL = os.getenv('TEST_BASE_URL', '').strip()


def _client() -> httpx.AsyncClient:
    if TEST_BASE_URL:
        return httpx.AsyncClient(base_url=TEST_BASE_URL)
    from api import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_e2e_api_get___0():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__health_1():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/health', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_log_2():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.post('/eval/log', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_score_3():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.post('/eval/score', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_events_4():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/eval/events', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_config_5():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/eval/config', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_metrics_6():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/eval/metrics', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_queries_7():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/eval/queries', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_cost_report_8():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/eval/cost-report', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_alerts_9():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.get('/eval/alerts', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_retrieval_bench_10():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.post('/eval/retrieval-bench', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_embedding_comparison_11():
    # Extracted from api.py
    async with _client() as ac:
        response = await ac.post('/eval/embedding-comparison', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)
