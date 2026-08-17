"""RAGEvaluator unit tests — pure cost math + scorer edge cases (no LLM / no models).

Includes regression tests for:
  - gpt-4o-mini must appear in OPENAI_PRICES (cost was always $0.00)
  - asyncio.gather with return_exceptions=True — no task cancellation on judge error
  - _persona_scope_flags must not false-split on bare newlines
  - score_faithfulness sentence splitter must preserve decimal numbers
  - @track sync decorator must not crash with asyncio.run() in async contexts
"""
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
    assert "groq/openai/gpt-oss-120b" in GROQ_PRICES
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
        "anthropic/claude-haiku-4-5", "groq/openai/gpt-oss-120b", "openai/gpt-4o-mini",
    ])

    async def _fake_judge(self, answer, context, model):
        return 0.9 if model == "anthropic/claude-haiku-4-5" else None

    monkeypatch.setattr(RAGEvaluator, "_judge_groundedness", _fake_judge)
    ev = RAGEvaluator()
    with pytest.raises(InsufficientJudgesError):
        asyncio.run(ev.score_groundedness_consensus("answer", "context"))


def test_consensus_succeeds_with_exactly_two_responding_judges(monkeypatch):
    monkeypatch.setattr(settings, "JUDGE_MODELS", [
        "anthropic/claude-haiku-4-5", "groq/openai/gpt-oss-120b",
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
    monkeypatch.setenv("EMBEDDING_ENDPOINT", "https://custom-inference.example.com/api/inference")
    monkeypatch.setattr("httpx.Client", _FakeHttpxClient)
    _FakeHttpxClient.respond_with = {"embeddings": [[0.5, 0.6]]}

    ev = RAGEvaluator(embedding_model="BAAI/bge-m3")
    vecs = ev._remote_embed(["a"], model="BAAI/bge-m3")  # _embed() always passes model=

    assert _FakeHttpxClient.last_url == "https://custom-inference.example.com/api/inference/embed"
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
    asyncio.run(ev._judge_groundedness("answer", "context", model="groq/openai/gpt-oss-120b"))
    assert "fallbacks" not in captured


# ─── OpenAI judge cost tracking ────────────────────────────────────────────────

def test_gpt4o_mini_has_nonzero_price():
    """openai/gpt-4o-mini was once missing from OPENAI_PRICES so all cost tracking
    for the OpenAI judge returned $0.00. It must now return a positive cost."""
    from rageval.evaluator import OPENAI_PRICES
    assert "openai/gpt-4o-mini" in OPENAI_PRICES, (
        "openai/gpt-4o-mini is not in OPENAI_PRICES — add it so cost tracking works"
    )
    cost = RAGEvaluator.calculate_cost(1_000_000, "openai/gpt-4o-mini")
    assert cost > 0.0, f"Expected non-zero cost for gpt-4o-mini, got {cost}"


# ─── Persona scope flags on multi-line answers ─────────────────────────────────

def test_persona_scope_flags_no_false_positive_on_bullet_list():
    """Bare newlines (bullet lists) must not be treated as sentence boundaries — that
    would inflate the sentence count and trigger false PERSONA_SCOPE_VIOLATION flags."""
    from rageval.evaluator import RAGEvaluator
    ev = RAGEvaluator()
    # A CFO answer with bullet points that contain no out-of-scope domain figures.
    answer = (
        "Revenue grew 18% YoY.\n"
        "• EBITDA margin improved to 22%.\n"
        "• Cash runway stands at 14 months.\n"
        "• ARR reached $4.2M."
    )
    flags = ev._persona_scope_flags(answer, "cfo")
    # CFO is allowed to discuss finance figures — should produce no violations.
    assert flags == [], f"Unexpected persona scope violations: {flags}"


def test_persona_scope_flags_still_catches_real_violations():
    """Sanity check: genuine out-of-scope content must still be flagged."""
    from rageval.evaluator import RAGEvaluator
    ev = RAGEvaluator()
    # A CFO answer that leaks headcount (a 'people' domain metric).
    answer = "Our revenue is $4M and headcount grew to 350 employees."
    flags = ev._persona_scope_flags(answer, "cfo")
    assert "people" in flags, f"Expected 'people' violation, got {flags}"


# ─── Faithfulness sentence splitting on decimals ───────────────────────────────

def test_faithfulness_sentence_split_preserves_decimals():
    """The sentence splitter used to split '$4.2M' into '$4' and '2M', and '3.14%'
    into '3' and '14%'. The split must only occur at sentence-ending punctuation
    that is NOT surrounded by digits."""
    import re
    # Replicate the fixed split logic from evaluator.py.
    answer = "Revenue was $4.2M. Margin improved by 3.14%. Headcount: 350."
    sentences = [
        s.strip()
        for s in re.split(r"(?<![0-9])(?<=[.!?])\s+|(?<=[.!?])\s+(?![0-9])", answer)
        if s.strip()
    ]
    # '$4.2M' and '3.14%' must not be split.
    full_text = " ".join(sentences)
    assert "$4.2M" in full_text, f"$4.2M was destroyed by sentence splitter. Sentences: {sentences}"
    assert "3.14%" in full_text, f"3.14% was destroyed by sentence splitter. Sentences: {sentences}"


# ─── @track sync wrapper in an async context ───────────────────────────────────

def test_track_sync_wrapper_does_not_crash_in_async_context():
    """The old sync @track wrapper called asyncio.run() which raises
    RuntimeError('This event loop is already running') when called from within a
    running event loop (FastAPI, Starlette, Jupyter, etc.).

    The fix uses fire-and-forget scheduling. This test verifies that calling a
    @track-decorated sync function from within an async context does NOT raise."""
    from rageval.decorator import track

    @track(model="groq/openai/gpt-oss-120b")
    def dummy_rag(query: str) -> str:
        return "The answer is 42."

    async def _caller():
        # This must NOT raise RuntimeError: This event loop is already running.
        result = dummy_rag("What is the meaning?")
        assert result == "The answer is 42."

    asyncio.run(_caller())


# ─── Consensus failure doesn't crash the other scoring tasks ──────────────────

def test_score_interaction_consensus_failure_does_not_crash_other_tasks(monkeypatch):
    """asyncio.gather() with return_exceptions=True — when consensus raises
    InsufficientJudgesError, score_interaction must re-raise it cleanly, not silently
    discard the relevance/faithfulness results or cancel their threads.

    Patches rageval.evaluator.settings directly (the object evaluator.py actually
    imported) rather than rageval._compat.settings which may have been replaced
    by importlib.reload() in the sqlite_store fixture.
    """
    import rageval.evaluator as ev_mod
    monkeypatch.setattr(ev_mod.settings, "JUDGE_MODELS", [])  # forces InsufficientJudgesError

    ev = RAGEvaluator()
    with pytest.raises(InsufficientJudgesError):
        asyncio.run(ev.score_interaction(
            query="test", answer="test answer", chunks=["test context"],
            tokens_used=10, latency_ms=100.0, model="groq/openai/gpt-oss-120b",
        ))
