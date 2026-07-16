import pytest
import time

@pytest.mark.unit
def test_otel_span_export_mocked():
    # Basic mock test to ensure span exporter doesn't crash
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_span"):
            time.sleep(0.01)
    except Exception as e:
        pytest.fail(f"OpenTelemetry export crashed: {e}")
