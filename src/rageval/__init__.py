"""RAGeval — drop-in LLMOps observability for RAG systems.

Public API (lazily imported so ``import rageval`` stays light and config/env
overrides are honoured at first use):
    track               decorator that auto-logs any RAG function call
    RAGEvaluator        relevance / groundedness / faithfulness / cost scorers
    init_rageval_table  initialise the (SQLite-default) store
    log_interaction     persist a scored interaction
    get_metrics         aggregate metrics for the dashboard / API
"""

try:  # single source of truth = the installed distribution version
    from importlib.metadata import version as _v, PackageNotFoundError
    try:
        __version__ = _v("omnismart-rageval")
    except PackageNotFoundError:
        __version__ = "0.0.0+local"
except Exception:  # pragma: no cover
    __version__ = "0.0.0+local"

__all__ = [
    "__version__",
    "track",
    "RAGEvaluator",
    "init_rageval_table",
    "log_interaction",
    "get_metrics",
]


def __getattr__(name: str):
    """Lazily resolve public API symbols (PEP 562)."""
    if name == "track":
        from rageval.decorator import track

        return track
    if name == "RAGEvaluator":
        from rageval.evaluator import RAGEvaluator

        return RAGEvaluator
    if name in {"init_rageval_table", "log_interaction", "get_metrics"}:
        from rageval import store

        return getattr(store, name)
    raise AttributeError(f"module 'rageval' has no attribute {name!r}")
