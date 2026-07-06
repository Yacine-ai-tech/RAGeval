# GAP_REPORT — RAGeval (redesign v2 — 2026-07-06)

## 1. API inventory (api.py + rageval/, verified)

| Route | Response shape |
|---|---|
| `GET /health` | `{status, service, version}` |
| `POST /eval/score` | `{relevance, groundedness, groundedness_consensus:{consensus, stdev, judges:[{model,score}], judges_used, flag_for_review}, faithfulness, cost_usd, latency_ms, tokens_used, model, persona, persona_scope_violations, overall_quality, flags[], needs_review}` |
| `POST /eval/log` | same as score; also persists to `rageval_log` |
| `GET /eval/metrics?days=` | `{total_queries, avg_relevance, avg_groundedness, avg_faithfulness, avg_latency_ms, total_cost_usd, flagged_count, query_volume_by_hour:[] (always empty)}` |
| `GET /eval/queries?limit=&needs_review=` | rows: `{id, timestamp, query, answer, persona, model, relevance, groundedness, faithfulness, cost_usd, latency_ms, tokens_used, flags(JSON str), session_id, needs_review}` |
| `GET /eval/cost-report?days=` | `{daily_costs, by_model, total_cost_usd, days}` |
| `GET /eval/alerts` | `{flagged_count, alerts:[query rows]}` |
| `POST /eval/retrieval-bench` | `{strategy_a_mean, strategy_b_mean, winner, per_query_a[], per_query_b[]}` |
| `POST /eval/embedding-comparison` | `{results:{model:score}, best}` |

Judges (core/config.py): `anthropic/claude-haiku-4-5`, `groq/llama-3.3-70b-versatile`,
`openai/gpt-5-mini` — unconfigured judges are SKIPPED (`judges_used` reflects real votes).
Persona scope checking is REAL (`persona_scope_violations` + `PERSONA_SCOPE_VIOLATION` flag).
Flags: LOW_RETRIEVAL_RELEVANCE, POTENTIAL_HALLUCINATION, HIGH_LATENCY, JUDGE_DISAGREEMENT,
PERSONA_SCOPE_VIOLATION.

## 2. P0 mapping — all supported

- Overview → `/eval/metrics` + `/eval/alerts`. `query_volume_by_hour` is always `[]` →
  time-series chart is computed client-side from `/eval/queries` timestamps (real data).
- Queries & Traces → `/eval/queries` (limit + needs_review filter); row expand shows all
  stored columns + parsed flags. Chunks are NOT persisted → no retrieved-context pane in
  history (only in live Evaluate results). Not a gap to fix — by design of the store.
- Evaluate → `POST /eval/score` (multi-judge panel from `groundedness_consensus.judges`);
  "Log interaction" → `POST /eval/log`.
- Cost → `/eval/cost-report`. Alerts → `/eval/alerts`.
- Experiments → `/eval/retrieval-bench` + `/eval/embedding-comparison` (both real).
- Instrumentation → factual `@track` snippet from README (`from rageval import track`).

## 3. Approved minor extensions — none

api.py changes limited to the additive SPA-serving block (same pattern as DocIntel).

## 4. Verified claims

- "One decorator" = `rageval/decorator.py` `@track(model=..., persona=...)`; pip package
  `omnismart-rageval` (import stays `rageval`).
- Multi-judge consensus + judge disagreement flag (stdev > 0.2, ≥2 judges) — real.
- Persona-aware evaluation — real (`_persona_scope_flags`).
- OpenTelemetry — NOT present in the package → OTel screen **cut** (per SPEC §6).

## 5. Real-vs-Demo table

| Screen | Source |
|---|---|
| Overview, Queries, Evaluate, Cost, Alerts, Experiments | real endpoints |
| Overview trend chart | real, derived client-side from /eval/queries |
| Instrumentation | factual static (README/PyPI) |
| Evaluate sample presets | prefilled example text clearly labeled "sample input" (scored for real) |
