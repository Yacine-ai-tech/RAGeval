# RAGeval Architecture

How RAGeval turns a (query, answer, retrieved chunks) triple into scored, persisted and
queryable telemetry. This page complements [`README.md`](README.md) (what it is and how to run
it), [`RESEARCH.md`](RESEARCH.md) (why the scoring is designed this way) and
[`BENCHMARK.md`](BENCHMARK.md) (measured accuracy). The interactive version lives in the
dashboard under **Architecture**.

## 1. System overview

```
 your RAG app ──@track / POST /eval/log──▶  API (FastAPI)
                                              │
                      ┌───────────────────────┼────────────────────────┐
                      ▼                       ▼                        ▼
              retrieval relevance     judge panel (LLMs)        faithfulness
              (embeddings)            groundedness consensus    (sentence ↔ chunk)
                      └───────────────┬───────┴────────────────────────┘
                                      ▼
                         overall quality, flags, cost
                                      ▼
                       store (SQLite | Postgres + pgvector)
                                      ▼
              dashboard · /eval/metrics · /eval/live · OpenTelemetry
```

Two ways to use it share one code base:

| Form | Entry point | Use when |
|---|---|---|
| Library (`omnismart-rageval`) | `from rageval import track` | instrument an existing app in-process |
| Service | `api.py` + dashboard SPA | central scoring and a shared dashboard |

## 2. Components

| Component | Role |
|---|---|
| Decorator (`@track`) | wraps a sync or async function; scoring runs in the background so the caller's return value is never delayed; `flush()` waits for pending work in short-lived scripts |
| Evaluator | computes relevance, faithfulness, groundedness consensus, cost and flags |
| Judge panel | independent LLM judges from different providers; at least two must answer |
| Key pool | discovers provider keys from the environment and rotates them, skipping a key that is rate-limited until its retry window ends |
| Embedder | one of three modes: in-process model, remote endpoint, or a lexical fallback |
| Store | SQLite by default; Postgres with pgvector for production; idempotent schema bootstrap |
| API | scoring, aggregation, event feed (poll and WebSocket), health and readiness |
| Dashboard | overview, queries, live traces, evaluate, experiments, cost, alerts, models, docs |
| Exporters | optional OTLP spans; DSPy metric binding |

## 3. What happens to one interaction

1. **Admit**: authenticate (optional shared token), rate-limit, validate sizes, resolve the
   visitor session, take one of a bounded number of evaluation slots.
2. **Score in parallel**
   - *Retrieval relevance*: embedding similarity between the query and each chunk.
   - *Groundedness consensus*: every judge rates whether the answer is supported by the chunks;
     scores are combined with accuracy-based weights (weighted mean or weighted median).
     Disagreement beyond a threshold flags the record for review.
   - *Faithfulness*: for each answer sentence, the best similarity to any chunk.
3. **Derive**: overall quality = 0.4 · relevance + 0.4 · groundedness + 0.2 · faithfulness; cost from
   token counts and a per-model price table; flags (`LOW_RETRIEVAL_RELEVANCE`,
   `POTENTIAL_HALLUCINATION`, `HIGH_LATENCY`, `JUDGE_DISAGREEMENT`, `PERSONA_SCOPE_VIOLATION`).
4. **Persist and publish**: write the record, push an event to live subscribers.

If fewer than two judges can answer, the request fails with HTTP 503. A single-judge score is
never presented as a consensus.

## 4. Design decisions

| Decision | Reason |
|---|---|
| Heterogeneous judge panel | correlated errors inside one provider family; a panel isolates outages and biases |
| No single-judge fallback | a silent downgrade would change what "consensus" means |
| Embedding backend chosen explicitly | swapping models silently would change relevance numbers between runs |
| Scoring off the caller's critical path | observability must not add latency to the application |
| Bounded bodies, concurrency and timeouts | protect a single-process deployment from oversized or bursty input |
| Dedicated database variable for the service | importing the library into another app can never write into that app's database |
| Session-scoped reads | anonymous visitors only see their own records; admin views are explicit |

## 5. Interfaces

| Route | Purpose |
|---|---|
| `POST /eval/log` | score and persist an interaction |
| `POST /eval/score` | score without persisting |
| `GET /eval/metrics`, `/eval/queries`, `/eval/cost-report`, `/eval/alerts` | aggregations |
| `GET /eval/config`, `/eval/events` | active panel, recent events |
| `WS /eval/live` | push feed |
| `POST /eval/retrieval-bench`, `/eval/embedding-comparison` | benchmarking helpers |
| `GET /health`, `GET /ready` | liveness; readiness (embedder warm and database reachable) |

Interactive API reference: `/docs` on a running instance, and the **API Docs** page.

## 6. Configuration

Everything is environment-driven; [`.env.example`](.env.example) lists every variable with
its purpose. Groups:

| Group | Examples |
|---|---|
| Judges | `JUDGE_MODELS`, `LLM_JUDGE`, `LLM_JUDGE_FALLBACK`, `JUDGE_TIMEOUT` |
| Embeddings | `USE_LOCAL_EMBEDDER`, `INFERENCE_MODE`, `EMBEDDING_ENDPOINT`, `EMBEDDING_MODEL` |
| Storage | `RAGEVAL_STORE`, `RAGEVAL_DB_PATH`, `RAGEVAL_POSTGRES_URL`, `RAGEVAL_EMBEDDING_DIM` |
| Scoring | `RAGEVAL_AGGREGATION_STRATEGY`, `RAGEVAL_INCLUDE_SYMBOLIC_JUDGE` |
| Limits | `RAGEVAL_MAX_REQUEST_BODY_BYTES`, `RAGEVAL_MAX_CONCURRENT_EVALUATIONS` |
| Access | `REQUIRE_INTERNAL_TOKEN`, `CORS_ALLOWED_ORIGINS`, `DEMO_SESSION_SCOPING` |
| Telemetry | `TELEMETRY_OPT_OUT`, `DO_NOT_TRACK` |

## 7. Startup and readiness

- Schema bootstrap runs before serving; a migration error stops startup.
- The embedding backend is warmed on a background thread; `/ready` reports `warming_up` (503)
  until it is loaded, then verifies a database query. Route traffic only after `/ready` is 200.

## 8. Privacy

The optional startup ping carries only the service name, version and a random installation id,
and is disabled by `TELEMETRY_OPT_OUT=true` or `DO_NOT_TRACK=1`. Queries, answers, scores and
keys are never transmitted.
