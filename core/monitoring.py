"""
Unified Metrics & Monitoring Service — Prometheus + psutil only.
"""
from __future__ import annotations

import psutil
from typing import Any, Dict

from prometheus_client import Counter, Histogram, Gauge

from core.logger import get_logger

log = get_logger(__name__)

# ── Prometheus metrics ───────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "request_count_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
ERROR_COUNT = Counter(
    "error_count_total", "Total errors", ["type", "module"]
)
TOKEN_USAGE = Counter(
    "ai_token_usage_total", "Total AI tokens consumed", ["model", "type"]
)
REQUEST_LATENCY = Histogram(
    "request_latency_seconds", "Request latency in seconds", ["endpoint"]
)
AI_LATENCY = Histogram(
    "ai_inference_seconds", "AI model inference time", ["model", "task"]
)
SYSTEM_MEMORY = Gauge("system_memory_usage_bytes", "Current RAM usage in bytes")
SYSTEM_CPU = Gauge("system_cpu_percent", "Current CPU usage percent")
ACTIVE_USERS = Gauge("active_users_count", "Number of currently active users")


# ── Monitor singleton ────────────────────────────────────────────────────────

class UnifiedMonitor:
    """Prometheus + psutil metrics — single instance."""

    _instance: "UnifiedMonitor | None" = None

    def __new__(cls) -> "UnifiedMonitor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── system ───────────────────────────────────────────────────────────────

    def collect_system_metrics(self) -> None:
        mem = psutil.virtual_memory()
        SYSTEM_MEMORY.set(mem.used)
        SYSTEM_CPU.set(psutil.cpu_percent(interval=None))

    # ── AI logging ───────────────────────────────────────────────────────────

    def log_ai_interaction(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency: float,
        success: bool = True,
    ) -> None:
        TOKEN_USAGE.labels(model=model, type="input").inc(input_tokens)
        TOKEN_USAGE.labels(model=model, type="output").inc(output_tokens)
        AI_LATENCY.labels(model=model, task="chat").observe(latency)
        if not success:
            ERROR_COUNT.labels(type="ai_error", module="chatbot").inc()

    # ── request logging ──────────────────────────────────────────────────────

    def log_request(self, method: str, endpoint: str, status: int, latency: float) -> None:
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)

    def log_error(self, error_type: str, module: str) -> None:
        ERROR_COUNT.labels(type=error_type, module=module).inc()

    # ── metric snapshot ──────────────────────────────────────────────────────

    def get_current_metrics(self) -> Dict[str, Any]:
        self.collect_system_metrics()

        def _sum_samples(metric):
            try:
                return sum(s.value for s in metric.collect()[0].samples)
            except Exception:
                return 0

        total_reqs = _sum_samples(REQUEST_COUNT)
        total_errs = _sum_samples(ERROR_COUNT)
        error_rate = (total_errs / total_reqs * 100) if total_reqs > 0 else 0.0

        lat_sum = lat_count = 0.0
        try:
            for s in REQUEST_LATENCY.collect()[0].samples:
                if s.name.endswith("_sum"):
                    lat_sum += s.value
                elif s.name.endswith("_count"):
                    lat_count += s.value
        except Exception:
            pass
        avg_latency_ms = (lat_sum / lat_count * 1000) if lat_count > 0 else 0.0

        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "error_rate": round(error_rate, 2),
            "avg_latency": round(avg_latency_ms, 2),
            "total_requests": int(total_reqs),
            "ai_tokens": int(_sum_samples(TOKEN_USAGE)),
        }


monitor = UnifiedMonitor()


def get_monitor() -> UnifiedMonitor:
    return monitor
