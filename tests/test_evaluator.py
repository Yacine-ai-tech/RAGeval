"""RAGEvaluator unit tests — pure cost math + scorer edge cases (no LLM / no models)."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rageval.evaluator import (  # noqa: E402
    ANTHROPIC_PRICES,
    GROQ_PRICES,
    InsufficientJudgesError,
    MIN_JUDGES_REQUIRED,
    RAGEvaluator,
)
from rageval._compat import settings  # noqa: E402


def test_calculate_cost_known_values():
    # 1M tokens @ Haiku (1.00 in / 5.00 out), 70/30 split → 0.7*1 + 0.3*5 = 2.20 USD
    cost = RAGEvaluator.calculate_cost(1_000_000, "anthropic/claude-haiku-4-5", input_ratio=0.7)
    assert abs(cost - 2.20) < 1e-6


def test_calculate_cost_unknown_model_is_zero():
    assert RAGEvaluator.calculate_cost(1_000_000, "unknown/model") == 0.0


def test_pricing_tables_have_core_models():
    assert "groq/llama-3.3-70b-versatile" in GROQ_PRICES
    assert "anthropic/claude-sonnet-4-6" in ANTHROPIC_PRICES


def test_retrieval_relevance_empty_is_zero():
    ev = RAGEvaluator()
    assert ev.score_retrieval_relevance("q", []) == 0.0


def test_evaluator_instantiates_without_loading_models():
    ev = RAGEvaluator()
    assert ev._embedder is None  # lazy — no model load at construction


def test_min_judges_required_is_two():
    assert MIN_JUDGES_REQUIRED == 2


def test_consensus_raises_when_fewer_than_two_judges_configured(monkeypatch):
    """Config-time check: JUDGE_MODELS listing < 2 models is a hard error, not a
    single-judge fallback."""
    monkeypatch.setattr(settings, "JUDGE_MODELS", ["anthropic/claude-haiku-4-5"])
    ev = RAGEvaluator()
    with pytest.raises(InsufficientJudgesError):
        asyncio.run(ev.score_groundedness_consensus("answer", "context"))


def test_consensus_raises_when_configured_judges_zero(monkeypatch):
    monkeypatch.setattr(settings, "JUDGE_MODELS", [])
    ev = RAGEvaluator()
    with pytest.raises(InsufficientJudgesError):
        asyncio.run(ev.score_groundedness_consensus("answer", "context"))


def test_consensus_raises_when_fewer_than_two_judges_respond(monkeypatch):
    """Runtime check: 2+ judges configured but only 1 actually responds (bad key,
    network error) still raises — no silent single-judge consensus, no swapping in a
    different judge as a fallback."""
    monkeypatch.setattr(settings, "JUDGE_MODELS", [
        "anthropic/claude-haiku-4-5", "groq/llama-3.3-70b-versatile", "openai/gpt-4o-mini",
    ])

    async def _fake_judge(self, answer, context, model):
        return 0.9 if model == "anthropic/claude-haiku-4-5" else None

    monkeypatch.setattr(RAGEvaluator, "_judge_groundedness", _fake_judge)
    ev = RAGEvaluator()
    with pytest.raises(InsufficientJudgesError):
        asyncio.run(ev.score_groundedness_consensus("answer", "context"))


def test_consensus_succeeds_with_exactly_two_responding_judges(monkeypatch):
    monkeypatch.setattr(settings, "JUDGE_MODELS", [
        "anthropic/claude-haiku-4-5", "groq/llama-3.3-70b-versatile",
    ])

    async def _fake_judge(self, answer, context, model):
        return 0.9 if "anthropic" in model else 0.7

    monkeypatch.setattr(RAGEvaluator, "_judge_groundedness", _fake_judge)
    ev = RAGEvaluator()
    result = asyncio.run(ev.score_groundedness_consensus("answer", "context"))
    assert result["judges_used"] == 2
    assert result["consensus"] == pytest.approx(0.8)


class _FakeHttpxResponse:
    def __init__(self, json_body):
        self._json = json_body

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


class _FakeHttpxClient:
    """Captures the request _remote_embed actually sends, no network."""
    last_url = None
    last_json = None
    respond_with = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json, headers):
        type(self).last_url = url
        type(self).last_json = json
        return _FakeHttpxResponse(type(self).respond_with)


def test_remote_embed_dispatches_hf_native_shape(monkeypatch):
    monkeypatch.setenv("INFERENCE_MODE", "remote")
    hf_url = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"
    monkeypatch.setenv("EMBEDDING_ENDPOINT", hf_url)
    monkeypatch.setattr("httpx.Client", _FakeHttpxClient)
    _FakeHttpxClient.respond_with = [[0.1, 0.2], [0.3, 0.4]]

    ev = RAGEvaluator()
    vecs = ev._remote_embed(["a", "b"])

    assert _FakeHttpxClient.last_url == hf_url  # called as-is, no /embed suffix
    assert _FakeHttpxClient.last_json == {"inputs": ["a", "b"]}  # HF's native shape
    assert vecs.shape == (2, 2)


def test_remote_embed_mean_pools_per_token_hf_response(monkeypatch):
    """A plain feature-extraction pipeline (not a sentence-embedding model) returns one
    vector per token — an extra nesting level that must be mean-pooled to one vector
    per input text."""
    monkeypatch.setenv("INFERENCE_MODE", "remote")
    monkeypatch.setenv("EMBEDDING_ENDPOINT", "https://router.huggingface.co/hf-inference/models/x")
    monkeypatch.setattr("httpx.Client", _FakeHttpxClient)
    _FakeHttpxClient.respond_with = [[[1.0, 1.0], [3.0, 3.0]]]  # 1 text, 2 tokens, 2 dims

    ev = RAGEvaluator()
    vecs = ev._remote_embed(["one text"])

    assert vecs.shape == (1, 2)
    assert vecs[0].tolist() == [2.0, 2.0]  # mean of the two token vectors


def test_remote_embed_dispatches_generic_contract(monkeypatch):
    monkeypatch.setenv("INFERENCE_MODE", "remote")
    monkeypatch.setenv("EMBEDDING_ENDPOINT", "https://orchestrator.example.com/api/inference")
    monkeypatch.setattr("httpx.Client", _FakeHttpxClient)
    _FakeHttpxClient.respond_with = {"embeddings": [[0.5, 0.6]]}

    ev = RAGEvaluator(embedding_model="BAAI/bge-m3")
    vecs = ev._remote_embed(["a"], model="BAAI/bge-m3")  # _embed() always passes model=

    assert _FakeHttpxClient.last_url == "https://orchestrator.example.com/api/inference/embed"
    assert _FakeHttpxClient.last_json == {"texts": ["a"], "model": "BAAI/bge-m3"}
    assert vecs.shape == (1, 2)


def test_judge_call_has_no_fallback_model_param(monkeypatch):
    """_judge_groundedness must not pass litellm's fallbacks= — a configured judge is
    used as-is or skipped, never silently swapped for a different model."""
    captured = {}

    async def _fake_acompletion(**kwargs):
        captured.update(kwargs)
        class _Msg:
            content = "0.8"
        class _Choice:
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
        return _Resp()

    import rageval.evaluator as evaluator_mod
    monkeypatch.setattr(evaluator_mod, "acompletion", _fake_acompletion)
    ev = RAGEvaluator()
    asyncio.run(ev._judge_groundedness("answer", "context", model="groq/llama-3.3-70b-versatile"))
    assert "fallbacks" not in captured
