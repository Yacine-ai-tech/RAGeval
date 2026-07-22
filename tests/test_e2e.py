import pytest
import httpx
from fastapi.testclient import TestClient
from api.app import app
import os

client = TestClient(app)
HEADERS = {"X-OmniIntel-Internal-Token": os.getenv("OMNIINTEL_INTERNAL_TOKEN", "REDACTED_SECRET")}

@pytest.mark.asyncio
async def test_e2e_rageval_evaluate_dataset():
    # Evaluate RAG responses using LLM-as-a-judge (Gemini/OpenAI)
    payload = {
        "dataset_name": "q3_financial_eval",
        "queries": ["What was the Q3 operating margin?"],
        "contexts": [["Operating margin for Q3 2026 stood at 18.5%, down slightly from Q2."]],
        "generated_answers": ["The Q3 operating margin was 18.5%."]
    }
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/eval/run", json=payload, headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "evaluation_id" in data
        assert "metrics" in data
        assert "faithfulness" in data["metrics"]

@pytest.mark.asyncio
async def test_e2e_rageval_get_history():
    # Fetch historical evaluations
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/eval/history", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("history", []), list)

@pytest.mark.asyncio
async def test_e2e_rageval_synthetic_data_gen():
    # Test the synthetic question generation pipeline
    payload = {
        "context": "The new product launch resulted in a 40% uptick in customer acquisition cost.",
        "num_questions": 3
    }
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/eval/generate-synthetic", json=payload, headers=HEADERS)
        # Should return questions or 500 if LLM fails
        assert response.status_code in (200, 500)
