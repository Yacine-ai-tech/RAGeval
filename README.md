# RAGeval

[![CI](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/omnismart-rageval.svg)](https://pypi.org/project/omnismart-rageval/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

**Drop-in LLMOps observability for RAG pipelines. Self-hosted. SQLite-default. Persona-aware. Multi-judge consensus.**

Version: **v0.1.22** | `pip install omnismart-rageval`

> 🔗 **Live demo:** https://rageval.ysiddo-ai-projects.app/ — browser dashboard (score a query + view metrics). Also fully scriptable — **API:** `/health`, `/eval/*` via `curl`/HTTPie.
> Self-hosting: see [SELF_HOSTING.md](SELF_HOSTING.md).

## The 60-Second Pitch

```python
from rageval import track

@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def answer_question(query: str, context_chunks: list[str]) -> str:
    ...
```

That's it. Open the dashboard at `localhost:8003`.

## What It Measures

| Metric                  | Definition                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| Retrieval relevance      | Cosine similarity between query and retrieved chunks (BGE-large by default) |
| Groundedness consensus   | Multi-judge LLM scoring across your configured `JUDGE_MODELS` (min. 2 — no single-judge fallback), flags disagreement |
| Faithfulness             | Per-sentence max-similarity to any chunk (NLI proxy)                        |
| Cost                     | USD per interaction, tracked by model                                       |
| Latency                  | End-to-end wall-clock                                                       |

See [RESEARCH.md](RESEARCH.md) for the reasoning behind an LLM-judge, multi-judge-consensus design, and [eval/JUDGE_BENCHMARK.md](eval/JUDGE_BENCHMARK.md) for measured accuracy against a hallucination benchmark.

## Comparison vs Alternatives

| Feature                | RAGeval  | Phoenix  | Langfuse | TruLens  |
|-------------------------|----------|----------|----------|----------|
| Self-hosted             | ✅       | ✅       | ✅       | ✅       |
| SQLite default           | ✅       | ❌       | ❌       | ❌       |
| Drop-in decorator        | ✅       | partial  | ❌       | partial  |
| Persona-aware            | ✅       | ❌       | ❌       | ❌       |
| Multi-judge consensus    | ✅       | ❌       | ❌       | ❌       |
| Cost tracking            | ✅       | ✅       | ✅       | partial  |
| Setup time               | 60 sec   | 10 min   | 15 min   | 10 min   |

_As of 2026, based on each project's public documentation. Feature sets change fast in this space — worth re-checking before you decide._

## Quick Start

```bash
pip install omnismart-rageval   # v0.1.22 — distribution name; CLI + import remain `rageval`
rageval init                    # creates ~/.rageval/rageval.db
rageval serve --port 8003
```

## Integration

### FastAPI

```python
from rageval import track

@app.post("/ask")
@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def ask(query: str):
    chunks = await retriever.search(query)
    return await llm.generate(query, chunks=chunks)
```

### LangChain

```python
@track(model="groq/openai/gpt-oss-120b")
def chain_invoke(query: str, context_chunks: list[str]):
    return chain.invoke({"query": query, "context": context_chunks})
```

## Endpoints

| Method | Path                          | Purpose                                  |
|--------|-------------------------------|-------------------------------------------|
| GET    | /health                       | Liveness                                  |
| POST   | /eval/log                     | Score + store                             |
| POST   | /eval/score                   | Score only (no storage)                   |
| GET    | /eval/metrics?days=7          | Aggregate dashboard data                  |
| GET    | /eval/queries                 | Query log (filter by needs_review)        |
| GET    | /eval/cost-report?days=30     | Cost breakdown by day + model             |
| GET    | /eval/alerts                  | Recent flagged queries                    |
| GET    | /eval/events                  | Recent evaluation-pipeline telemetry      |
| GET    | /eval/config                  | Judge/embedding/threshold configuration   |
| POST   | /eval/retrieval-bench         | A/B compare retrieval strategies          |
| POST   | /eval/embedding-comparison    | Compare embedding models                  |
| WS     | /eval/live                    | Real-time event feed                      |

Full reference with request/response shapes: the in-app **API Docs** page (`/api-docs` in the dashboard), or [SELF_HOSTING.md](SELF_HOSTING.md).

## Tests

50 test functions across smoke, API, evaluator, decorator, DSPy integration, store, and e2e:

```bash
pytest tests/ -q
```

## License & Commercial Use

This project is open-source under **AGPL-3.0** — free for researchers, students, and open-source use.

The AGPLv3 requires that any proprietary network service (SaaS, internal corporate tooling) that uses or modifies this code also open-source its entire backend. If you need to use RAGeval in a closed-source commercial environment, or need enterprise features (SSO, custom RBAC, etc.), see [COMMERCIAL.md](COMMERCIAL.md) for a commercial license.

## Anonymous Telemetry

RAGeval sends a single anonymous startup ping (a timestamp + a random, non-hardware-derived install ID — no API keys, prompts, or application data) so the maintainer can gauge usage. Disable it by setting `TELEMETRY_OPT_OUT=true` in your `.env`. See [TELEMETRY.md](TELEMETRY.md) for details.
