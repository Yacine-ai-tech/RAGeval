import pytest
import asyncio
from rageval.evaluator import RAGEvaluator

@pytest.mark.asyncio
async def test_rageval_evaluator_initialization():
    ev = RAGEvaluator()
    assert ev is not None

@pytest.mark.asyncio
async def test_rageval_score_interaction_mocked(monkeypatch):
    ev = RAGEvaluator()
    
    # Mock the internal judge method to avoid real API costs or missing key errors during unit tests
    async def mock_judge(*args, **kwargs):
        return 0.9
        
    monkeypatch.setattr(ev, "_judge_groundedness", mock_judge)

    res = await ev.score_interaction(
        query="What is the capital of France?",
        answer="The capital of France is Paris.",
        chunks=["Paris is the capital and most populous city of France."],
        tokens_used=10,
        latency_ms=100.0,
        model="groq/openai/gpt-oss-120b"
    )
    
    assert res is not None
    assert "groundedness" in res
    assert "relevance" in res
    assert "faithfulness" in res
