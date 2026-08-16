"""
core/monitoring.py — REMOVED (DEFECT-14)

This module previously contained a Prometheus + psutil UnifiedMonitor class
that was never imported by api.py or any other module in this project.
It depended on prometheus_client and psutil, which are not in requirements.txt
and would fail at import. Kept as empty stub to avoid ImportError for any
external code that might reference it.

Actual operational metrics are surfaced via /eval/metrics, /eval/cost-report,
and the in-process telemetry ring (_EVENTS) in api.py.
"""
