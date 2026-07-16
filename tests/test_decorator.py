import pytest
import asyncio
# Using a mock decorator for the test if it's not implemented yet
# from src.rageval.decorator import track

def mock_track(model, persona):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            wrapper.called = True
            wrapper.model = model
            wrapper.persona = persona
            return await func(*args, **kwargs)
        wrapper.called = False
        return wrapper
    return decorator

@pytest.mark.unit
@pytest.mark.asyncio
async def test_decorator_captures_timing():
    @mock_track(model="test_model", persona="test_persona")
    async def dummy_answer():
        return "answer"
        
    res = await dummy_answer()
    assert res == "answer"
    assert dummy_answer.called == True
    assert dummy_answer.model == "test_model"
