"""LIVE multi-judge consensus test — makes REAL LLM judge calls (needs ANTHROPIC_API_KEY or
GROQ_API_KEY in env). Validates the central RAGeval claim: consensus separates a grounded answer
from a hallucinated one, and judge disagreement is reported. Skipped when no key is configured."""
import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.skipif(
    not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("GROQ_API_KEY")),
    reason="live test needs an LLM key (ANTHROPIC_API_KEY/GROQ_API_KEY)",
)

CONTEXT = "Acme Corp Q2 revenue was $4.2M, up 20% year over year. Headcount is 50 employees."
GROUNDED = "Acme's Q2 revenue was $4.2M, a 20% year-over-year increase, with 50 staff."
HALLUCINATED = "Acme's Q2 revenue was $90M and the company employs over 5,000 people."


def test_consensus_separates_grounded_from_hallucinated():
    from rageval.evaluator import RAGEvaluator
    ev = RAGEvaluator()
    g = asyncio.run(ev.score_groundedness_consensus(GROUNDED, CONTEXT))
    h = asyncio.run(ev.score_groundedness_consensus(HALLUCINATED, CONTEXT))
    print(f"\nLIVE judges → grounded={g['consensus']:.2f} (stdev {g['stdev']:.2f}), "
          f"hallucinated={h['consensus']:.2f} (stdev {h['stdev']:.2f}), judges={len(g['judges'])}")
    assert len(g["judges"]) >= 1               # real judges ran
    assert g["consensus"] > h["consensus"]     # grounded scores strictly higher
    assert g["consensus"] >= 0.6               # grounded is accepted
    assert h["consensus"] <= 0.6               # hallucinated is flagged-low
