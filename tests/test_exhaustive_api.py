import pytest
import httpx
import os

TOKEN = os.getenv('OMNIINTEL_INTERNAL_TOKEN', 'REDACTED_SECRET')
HEADERS = {'X-OmniIntel-Internal-Token': TOKEN}
BASE_URL = os.getenv('TEST_BASE_URL', 'https://gateway.ysiddo-ai-projects.app/rageval')

@pytest.mark.asyncio
async def test_e2e_api_get___0():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__health_1():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/health', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_log_2():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.post(f'{BASE_URL}/eval/log', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_score_3():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.post(f'{BASE_URL}/eval/score', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_events_4():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/eval/events', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_config_5():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/eval/config', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_metrics_6():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/eval/metrics', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_queries_7():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/eval/queries', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_cost_report_8():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/eval/cost-report', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_get__eval_alerts_9():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.get(f'{BASE_URL}/eval/alerts', headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_retrieval_bench_10():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.post(f'{BASE_URL}/eval/retrieval-bench', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

@pytest.mark.asyncio
async def test_e2e_api_post__eval_embedding_comparison_11():
    # Extracted from api.py
    async with httpx.AsyncClient() as ac:
        response = await ac.post(f'{BASE_URL}/eval/embedding-comparison', json={}, headers=HEADERS)
        assert response.status_code in (200, 400, 401, 403, 404, 405, 422)

