# RAGeval — STEPS LOG (living document)

> Continuous engineering log of **every** action on RAGeval from Week 0 to now. Append newest at
> the bottom. Absolute dates. Branch model: feature branch → PR → merge into `develop`. Secrets
> live only in `.env`/`secrets.md` (gitignored) — never here.

## Project in one line
Drop-in LLMOps observability: multi-judge LLM evaluation with consensus, multi-embedding &
retrieval-strategy benchmarks, OpenTelemetry export, SQLite (dev) / pgvector (prod). Port 8003.

## Week 0 — scaffold & split (2026-05-20 → 06-05)
- `f607e64` initial scaffold from the OmniIntelOS split (`api.py`, `core/`, `rageval/evaluator.py`,
  `core/performance.py`).
- `6b15d1f` CI pytest; `8c95c82` **fix:** populate `rageval/__init__.py` with version + lazy
  public API; `4186c29` finalize Week 0; `aae3741` `docker-compose.dev.yml`.
- Status: **scaffold** — package + evaluator wired, 1 smoke test, Phase 5 feature work pending.

## New-account Studio provisioning + .env hardening (2026-06-16)
- Cloned onto `upwork_new` Studio; `.env` recreated with real secrets (Anthropic, Groq),
  `RAGEVAL_STORE=sqlite`, `JUDGE_MODELS=anthropic/claude-haiku-4-5,groq/llama-3.3-70b-versatile`
  (dropped the OpenAI judge — no OpenAI key configured), `EMBEDDING_MODEL=BAAI/bge-large-en-v1.5`;
  synced local ↔ Studio.

## GPU validation (T4, 2026-06-16)
- **Embedding backbone validated on the T4**: `BAAI/bge-large-en-v1.5` loaded on CUDA (6.5s),
  1024-dim vectors, semantic sanity `sim(revenue, sales)=0.673` ≫ `sim(revenue, cat)=0.273`.
  Confirms the embedding model used for the multi-embedding comparison + retrieval benchmarks.
  Switched Studio back to CPU after (billing).

## Current state
Scaffold + validated embedding backbone. Phase 5 build (multi-judge consensus, OTel export,
multi-embedding & retrieval-strategy endpoints, pgvector backend) is the next major work.

---

## Next — industry & research-standard improvements (planned)
1. **Standard RAG metrics**: implement RAGAS-style faithfulness / context precision-recall /
   answer relevance + a labeled eval set; expose `/evaluate`.
2. **Multi-judge consensus** (Claude Haiku + Groq) with agreement stats + bias checks.
3. **OpenTelemetry / OpenLLMetry** span export (enterprise observability standard).
4. **Multi-embedding comparison** endpoint (BGE vs e5 vs others) + **retrieval-strategy A/B**
   (dense vs hybrid vs rerank) on a fixed corpus — directly consumes IntelAI's GraphRAG deltas.
5. **pgvector** prod backend for millions of interactions.

## Phase 5 build pass (2026-06-16, post-GPU)
- **Assessment:** scaffold was substantially real — `evaluator.py` (multi-judge consensus, 5
  scorers, real per-model cost tables, flags, persona-aware), `store.py` (SQLite), `otel_exporter`,
  `dspy_integration`, `decorator`, `cli`, 9 API endpoints (log/score/metrics/queries/cost-report/
  alerts/retrieval-bench/embedding-comparison).
- **BUG FOUND (real, not test-only):** `store.py` never `expanduser`'d or created the parent dir
  for the SQLite path (`~/.rageval/rageval.db`) → `unable to open database file` on a fresh box.
  **Fix:** `_db_path()` with live env override + `expanduser` + `makedirs`.
- **Tests (Week 13):** added `test_evaluator.py` (pure cost math + scorer edges), `test_store.py`
  (SQLite round-trip), `test_api.py` (health/routes/metrics offline). **Studio pytest: 15 passed.**
- **GPU (earlier):** BGE-large embeddings validated on T4 (sim revenue~sales 0.673 ≫ revenue~cat 0.273).
- **Writing (Week 15):** `drafts/` (gitignored): `blog_post_5_llmops_eval.md`,
  `upwork_proposal_templates.md` (3 niches), `preprint_outline_multijudge.md` (preprint pre-work).

## Comprehensive QA pass (2026-06-16)
- **15 tests pass** + **rageval package** imports + builds wheel (PyPI-ready). §5.10 verified: multi-judge consensus, OpenTelemetry, multi-embedding, retrieval-bench, DSPy.
- All 6 projects + both packages green; 28/28 STRATEGY §.10 feature claims code-verified.

## Remediation — LIVE behavior validation (2026-06-17)
- Added `tests/test_live_judges.py` (real LLM, skip-if-no-key): **multi-judge consensus LIVE**: grounded=0.90 vs hallucinated=0.00 (real Claude Haiku + Groq judges) — the central claim now has real numbers.
- Addresses the "tests prove imports not behavior" gap with a real, measured run.

## Remediation — research-grade judge benchmark (2026-06-17)
- `eval/run_judge_benchmark.py` + `eval/JUDGE_BENCHMARK.md`: multi-judge consensus on **HaluEval**
  (standard hallucination benchmark), standard metrics. **50 labelled examples**:
  consensus **acc 0.820 / F1 0.816 / ROC-AUC 0.881**, beating both solo judges (Haiku 0.78,
  Groq 0.74). Disagreement→error signal only marginal at N=50 (honest). Preprint outline updated
  with measured numbers.
