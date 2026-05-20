"""
RAGeval @track decorator — drop-in observability for any RAG function.
"""
from __future__ import annotations

import asyncio
import functools
import time
import uuid
from typing import Any, Callable, List, Optional

from .evaluator import RAGEvaluator
from .store import log_interaction

_EVALUATOR = RAGEvaluator()


def track(model: str = "groq/llama-3.3-70b-versatile", persona: Optional[str] = None):
    """
    Decorator that auto-logs interactions to the RAGeval store.

    Wraps both sync and async functions. The wrapped function should accept
    `query` as its first arg and return the answer (string) or a dict with
    `answer` and optionally `chunks` keys.

    Usage::

        @track(model="anthropic/claude-sonnet-4-6", persona="cfo")
        async def answer_question(query: str, context_chunks: list[str]) -> str:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def aw(*args, **kwargs):
                query = args[0] if args else kwargs.get("query", "")
                chunks: List[str] = kwargs.get("context_chunks") or kwargs.get("chunks") or []
                t0 = time.time()
                result = await fn(*args, **kwargs)
                latency_ms = (time.time() - t0) * 1000
                answer, chunks_out = _unpack(result, chunks)
                scores = await _EVALUATOR.score_interaction(
                    query=query, answer=answer, chunks=chunks_out,
                    tokens_used=len(answer.split()) + sum(len(c.split()) for c in chunks_out),
                    latency_ms=latency_ms, model=model, persona=persona,
                )
                await log_interaction(query, answer, persona, scores, session_id=str(uuid.uuid4()))
                return result
            return aw

        @functools.wraps(fn)
        def sw(*args, **kwargs):
            query = args[0] if args else kwargs.get("query", "")
            chunks: List[str] = kwargs.get("context_chunks") or kwargs.get("chunks") or []
            t0 = time.time()
            result = fn(*args, **kwargs)
            latency_ms = (time.time() - t0) * 1000
            answer, chunks_out = _unpack(result, chunks)
            scores = asyncio.run(_EVALUATOR.score_interaction(
                query=query, answer=answer, chunks=chunks_out,
                tokens_used=len(answer.split()) + sum(len(c.split()) for c in chunks_out),
                latency_ms=latency_ms, model=model, persona=persona,
            ))
            asyncio.run(log_interaction(query, answer, persona, scores, session_id=str(uuid.uuid4())))
            return result
        return sw
    return decorator


def _unpack(result: Any, default_chunks: List[str]) -> tuple[str, List[str]]:
    if isinstance(result, dict):
        return result.get("answer", str(result)), result.get("chunks", default_chunks)
    return str(result), default_chunks
