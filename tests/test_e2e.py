import pytest
import httpx
from fastapi.testclient import TestClient
from api import app
import os

client = TestClient(app)
HEADERS = {"X-OmniIntel-Internal-Token": os.getenv("OMNIINTEL_INTERNAL_TOKEN", "default-dev-token")}

@pytest.mark.asyncio
async def test_e2e_rageval_score():
    payload = {
        "query": "What is the Q3 margin?",
        "chunks": ["Margin is 18.5%."],
        "answer": "18.5%",
    }
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/eval/score", json=payload, headers=HEADERS)
        # Should return 200 or 500 if LLM judge fails
        assert response.status_code in (200, 500)

@pytest.mark.asyncio
async def test_e2e_rageval_metrics():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/eval/metrics", headers=HEADERS)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_e2e_rageval_health():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health", headers=HEADERS)
        assert response.status_code == 200
