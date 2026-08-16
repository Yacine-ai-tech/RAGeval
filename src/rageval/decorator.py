"""
RAGeval @track decorator — drop-in observability for any RAG function.

The sync wrapper previously called asyncio.run() which raises
``RuntimeError: This event loop is already running`` whenever the decorated sync
function is invoked from within a running async event loop (FastAPI route, Jupyter
notebook, Starlette, etc.) — the primary production use-case.

Fix strategy: prefer scheduling background tasks on the already-running loop
(fire-and-forget, non-blocking), and only fall back to asyncio.run() when there
truly is no running loop (script / __main__ / pure-sync test contexts).
The sync-wrapper variant intentionally does NOT await results so it remains a
transparent drop-in replacement: the caller's return value is returned immediately
and the RAGeval scoring/logging happens asynchronously in the background.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import threading
import time
import uuid
from typing import Any, Callable, List, Optional

from .evaluator import RAGEvaluator
from .store import log_interaction

_EVALUATOR = RAGEvaluator()

# Dedicated single-thread event loop for background fire-and-forget tasks that
# originate from sync wrapper calls when the calling thread has no running loop.
# This avoids creating/destroying a new loop per call and is safe from thread-safety
# issues because all scheduling goes through loop.call_soon_threadsafe.
_bg_loop: Optional[asyncio.AbstractEventLoop] = None
_bg_loop_lock = threading.Lock()


def _get_bg_loop() -> asyncio.AbstractEventLoop:
    global _bg_loop
    with _bg_loop_lock:
        if _bg_loop is None or _bg_loop.is_closed():
            _bg_loop = asyncio.new_event_loop()
            t = threading.Thread(target=_bg_loop.run_forever, daemon=True, name="rageval-bg-loop")
            t.start()
    return _bg_loop


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine as a fire-and-forget task, handling both sync and async contexts."""
    try:
        loop = asyncio.get_running_loop()
        # There is already a running loop (FastAPI, Starlette, Jupyter, etc.) —
        # create a Task on that loop.  This is the primary production path.
        loop.create_task(coro)
    except RuntimeError:
        # No running loop (pure-sync context: CLI script, tests, __main__) —
        # delegate to the dedicated background loop.
        asyncio.run_coroutine_threadsafe(coro, _get_bg_loop())


async def _eval_and_log(
    query: str,
    answer: str,
    chunks: List[str],
    model: str,
    persona: Optional[str],
    latency_ms: float,
) -> None:
    """Evaluate and persist one interaction (awaitable, safe in any context)."""
    try:
        scores = await _EVALUATOR.score_interaction(
            query=query,
            answer=answer,
            chunks=chunks,
            tokens_used=len(answer.split()) + sum(len(c.split()) for c in chunks),
            latency_ms=latency_ms,
            model=model,
            persona=persona,
        )
        await log_interaction(query, answer, persona, scores, session_id=str(uuid.uuid4()))
    except Exception as e:
        # Never propagate exceptions from background telemetry into the user's call stack.
        import logging
        logging.getLogger(__name__).warning("RAGeval background eval failed: %s", e)


def track(model: str = "groq/llama-3.3-70b-versatile", persona: Optional[str] = None):
    """
    Decorator that auto-logs interactions to the RAGeval store.

    Wraps both sync and async functions. The wrapped function should accept
    ``query`` as its first arg and return the answer (string) or a dict with
    ``answer`` and optionally ``chunks`` keys.

    Usage::

        @track(model="anthropic/claude-haiku-4-5", persona="cfo")
        def answer_question(query: str, context_chunks: list[str]) -> str:
            ...

        @track(model="groq/llama-3.3-70b-versatile")
        async def answer_async(query: str, chunks: list[str]) -> str:
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
                # Async path: evaluate and log inline (we are already in an async context).
                await _eval_and_log(query, answer, chunks_out, model, persona, latency_ms)
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
            # Sync path: fire-and-forget — never blocks the caller, never crashes
            # with "event loop is already running" inside FastAPI/async contexts.
            _fire_and_forget(_eval_and_log(query, answer, chunks_out, model, persona, latency_ms))
            return result
        return sw
    return decorator


def _unpack(result: Any, default_chunks: List[str]) -> tuple[str, List[str]]:
    if isinstance(result, dict):
        return result.get("answer", str(result)), result.get("chunks", default_chunks)
    return str(result), default_chunks
