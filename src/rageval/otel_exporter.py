"""
RAGeval OpenTelemetry / OpenLLMetry exporter.

When RAGEVAL_OTEL_ENDPOINT is set, log records and scores are exported as
OpenTelemetry spans for enterprise interoperability.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rageval._compat import settings, get_logger  # self-contained (works when pip-installed)

log = get_logger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    _OTEL = True
except ImportError:
    _OTEL = False
    log.warning("opentelemetry not installed — otel_exporter inactive")


_provider: Optional[Any] = None
_tracer: Optional[Any] = None


def init_otel(endpoint: Optional[str] = None) -> bool:
    """Initialize the OTel pipeline. Idempotent."""
    global _provider, _tracer
    if not _OTEL:
        return False
    endpoint = endpoint or settings.RAGEVAL_OTEL_ENDPOINT
    if not endpoint:
        return False
    if _provider is None:
        _provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        _provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(_provider)
        _tracer = trace.get_tracer("rageval")
    return True


def export_span(name: str, attrs: Dict[str, Any]) -> None:
    """Export a single span. No-op if OTel is not initialized."""
    if _tracer is None:
        return
    with _tracer.start_as_current_span(name) as span:
        for k, v in attrs.items():
            try:
                span.set_attribute(k, v if isinstance(v, (str, int, float, bool)) else str(v))
            except Exception:
                import logging; logging.error('Unhandled exception', exc_info=True)
                pass
