"""
RAGeval DSPy integration — log compilation runs as RAGeval events.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from .store import log_interaction


async def log_dspy_run(
    program_name: str,
    candidates: list,
    winner: Any,
    eval_metric: str,
    eval_score: float,
) -> None:
    """Persist a DSPy compilation event."""
    summary = (
        f"DSPy compile: program={program_name}, candidates={len(candidates)}, "
        f"winner={winner}, metric={eval_metric}={eval_score}"
    )
    scores: Dict[str, Any] = {
        "model": f"dspy:{program_name}",
        "relevance": eval_score, "groundedness": eval_score, "faithfulness": eval_score,
        "cost_usd": 0.0, "latency_ms": 0.0, "tokens_used": 0, "flags": [],
    }
    await log_interaction(
        query=f"dspy_compile::{program_name}",
        answer=summary,
        persona="dspy_research",
        scores=scores,
    )
