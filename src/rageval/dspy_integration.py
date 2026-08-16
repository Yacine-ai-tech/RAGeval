"""
RAGeval DSPy integration — log compilation runs as RAGeval events.

The sync wrapper previously called asyncio.run() which raises
``RuntimeError: This event loop is already running`` in any async context.
Now uses the same fire-and-forget helper from decorator.py so it is safe
in both sync and async calling contexts.

This module never imports ``dspy`` itself: it only accepts already-computed
program_name/candidates/winner/eval_metric/eval_score values, so it works
whether or not ``dspy-ai`` is installed on the caller's side. Two ways in:

    await log_dspy_run(program_name=..., candidates=..., winner=..., ...)

or, wrap the function that performs the compilation and returns those fields
as a dict:

    @dspy_compile_callback
    def compile_program():
        optimizer = dspy.BootstrapFewShot(metric=my_metric)
        compiled = optimizer.compile(MyProgram(), trainset=trainset)
        return {"program_name": "my_program", "candidates": trainset,
                "winner": compiled, "eval_metric": "accuracy", "eval_score": 0.82}
"""
from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, Dict

from .store import log_interaction
from .decorator import _fire_and_forget  # shared fire-and-forget helper


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


def _extract(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "program_name": result["program_name"],
        "candidates": result.get("candidates", []),
        "winner": result.get("winner"),
        "eval_metric": result.get("eval_metric", "score"),
        "eval_score": result.get("eval_score", 0.0),
    }


def dspy_compile_callback(fn: Callable[..., Dict[str, Any]]) -> Callable[..., Any]:
    """Decorator for a function that runs a DSPy compilation and returns a dict with
    program_name/candidates/winner/eval_metric/eval_score. Logs the run to RAGeval
    after ``fn`` returns, then returns ``fn``'s original result unchanged. Works with
    sync or async ``fn``.
    """
    if asyncio.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def aw(*args: Any, **kwargs: Any) -> Any:
            result = await fn(*args, **kwargs)
            await log_dspy_run(**_extract(result))
            return result
        return aw

    @functools.wraps(fn)
    def sw(*args: Any, **kwargs: Any) -> Any:
        result = fn(*args, **kwargs)
        # Fire-and-forget instead of asyncio.run() — safe in both sync and async
        # calling contexts (no RuntimeError in FastAPI/Jupyter etc.).
        _fire_and_forget(log_dspy_run(**_extract(result)))
        return result
    return sw
