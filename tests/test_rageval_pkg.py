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
    
    # Mock the internal litellm call to avoid real API costs during tests
    async def mock_acompletion(*args, **kwargs):
        class MockMessage:
            content = '{"groundedness": 0.9, "completeness": 0.8}'
        class MockChoice:
            message = MockMessage()
        class MockResponse:
            choices = [MockChoice()]
        return MockResponse()
        
    import rageval.evaluator
    monkeypatch.setattr(rageval.evaluator, "acompletion", mock_acompletion)

    res = await ev.score_interaction(
        query="What is the capital of France?",
        answer="The capital of France is Paris.",
        chunks=["Paris is the capital and most populous city of France."],
        tokens_used=10,
        latency_ms=100.0,
        model="groq/llama-3.3-70b-versatile"
    )
    
    assert res is not None
    assert "groundedness" in res
    assert "relevance" in res
    assert "faithfulness" in res
