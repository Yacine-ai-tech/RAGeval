"""
core/performance.py — REMOVED (DEFECT-14)

This module previously contained constants (DB_POOL_SIZE, RATE_LIMIT_PER_MINUTE,
API_TIMEOUT, etc.) and warning-suppression side-effects that executed on import.
It was never imported by api.py or any other module, so none of those constants
controlled any actual behaviour — they were completely false documentation.

The module is kept as an empty stub to avoid ImportError for any external code
that might have imported it, but it now does nothing.

Rate limiting is now implemented via slowapi in api.py (DEFECT-11 fix).
DB pooling is handled by psycopg2's connection-per-call pattern in store.py.
"""
