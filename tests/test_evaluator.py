"""RAGEvaluator unit tests — pure cost math + scorer edge cases (no LLM / no models)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rageval.evaluator import ANTHROPIC_PRICES, GROQ_PRICES, RAGEvaluator  # noqa: E402


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
