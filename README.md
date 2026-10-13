# RAGeval

[![CI](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/omnismart-rageval.svg)](https://pypi.org/project/omnismart-rageval/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Live App](https://img.shields.io/badge/Live_App-rageval-0070f3?style=flat)](https://rageval.ysiddo-ai-projects.app)
[![Research](https://img.shields.io/badge/Research-Heterogeneous_Panel-8a2be2?style=flat)](https://rageval.ysiddo-ai-projects.app/research)
[![Benchmarks](https://img.shields.io/badge/Benchmarks-ROC--AUC_0.9191-green?style=flat)](https://rageval.ysiddo-ai-projects.app/benchmarks)
[![Guide](https://img.shields.io/badge/Docs-User_Guide-blue?style=flat)](https://rageval.ysiddo-ai-projects.app/guide)

**Self-hosted LLMOps observability for RAG pipelines, with multi-judge consensus scoring,
persona-scope detection, and a drop-in Python decorator.**

`pip install omnismart-rageval`

**Live application:** [rageval.ysiddo-ai-projects.app](https://rageval.ysiddo-ai-projects.app). Score queries and inspect consensus telemetry as it arrives.
- **Research Background:** [`RESEARCH.md`](RESEARCH.md) / [Online Research Documentation](https://rageval.ysiddo-ai-projects.app/research)
- **Empirical Benchmarks:** [`BENCHMARK.md`](BENCHMARK.md) / [Online Benchmark Dashboard](https://rageval.ysiddo-ai-projects.app/benchmarks)
- **User Guide:** [Online User Guide](https://rageval.ysiddo-ai-projects.app/guide)
- **Self-Hosting Guide:** [`SELF_HOSTING.md`](SELF_HOSTING.md)

## Overview

```python
from rageval import track

@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def answer_question(query: str, context_chunks: list[str]) -> str:
    ...
```

Instrumenting a RAG pipeline requires adding this decorator; the dashboard at `localhost:8003`
then reports groundedness, faithfulness, retrieval relevance, cost, and latency for every
call.

## What It Measures

| Metric | Definition |
|--------|-------------|
| Retrieval relevance | Cosine similarity between query and retrieved chunks (BGE-large by default) |
| Groundedness consensus | Multi-judge LLM scoring across a configured judge panel (minimum two judges; no single-judge fallback), with disagreement flagged for review |
| Faithfulness | Per-sentence maximum similarity to any retrieved chunk (an NLI proxy) |
| Cost | USD per interaction, tracked by model |
| Latency | End-to-end wall-clock time |

The reasoning behind an LLM-judge, multi-judge-consensus design is in [RESEARCH.md](RESEARCH.md);
measured accuracy against a hallucination-detection benchmark is in
[eval/JUDGE_BENCHMARK.md](eval/JUDGE_BENCHMARK.md).

## Comparison

| Feature | RAGeval | Phoenix | Langfuse | TruLens |
|---------|---------|---------|----------|---------|
| Self-hosted | Yes | Yes | Yes | Yes |
| SQLite by default | Yes | No | No | No |
| Drop-in decorator | Yes | Partial | No | Partial |
| Persona-scope detection | Yes | No | No | No |
| Multi-judge consensus | Yes | No | No | No |
| Cost tracking | Yes | Yes | Yes | Partial |

Based on each project's public documentation as of 2026; feature sets in this space change
quickly and are worth re-checking independently.

## Quick Start

```bash
pip install omnismart-rageval
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

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Liveness check |
| GET | /ready | Database readiness check; returns 503 until the schema can be queried |
| POST | /eval/log | Score and persist an interaction |
| POST | /eval/score | Score only, without persisting |
| GET | /eval/metrics?days=7 | Aggregate dashboard data |
| GET | /eval/queries | Query log, filterable by review status |
| GET | /eval/cost-report?days=30 | Cost breakdown by day and model |
| GET | /eval/alerts | Recently flagged queries |
| GET | /eval/events | Evaluation-pipeline event log |
| GET | /eval/config | Current judge, embedding, and threshold configuration |
| POST | /eval/retrieval-bench | Compare retrieval strategies against a fixed eval set |
| POST | /eval/embedding-comparison | Compare embedding models on the same eval set |
| WS | /eval/live | Real-time event feed |

Full request/response schemas are documented on the dashboard's built-in API Docs page
(`/api-docs`).

The API rejects request bodies larger than 1 MiB by default. Evaluation and comparison
requests are also bounded to 10 queries, 20 chunks per query, 4,000 characters per text,
and 200,000 total input characters. At most two expensive evaluation requests run at once
per process by default; saturated requests receive HTTP 503 with `Retry-After: 2`. Tune
`RAGEVAL_MAX_REQUEST_BODY_BYTES` and `RAGEVAL_MAX_CONCURRENT_EVALUATIONS` for the memory
and CPU budget of the deployment. Provider calls use `JUDGE_TIMEOUT` (default 90 seconds,
maximum 300) and remote embeddings use `EMBED_TIMEOUT` (default 30 seconds, maximum 120).

The API initializes and migrates its schema before serving requests. A failed schema
bootstrap aborts startup rather than leaving a partially usable service; `/health` remains
a liveness probe and `/ready` verifies database availability.

## Tests

100+ test functions across smoke, API, evaluator, decorator, DSPy integration, storage, and
end-to-end paths:

```bash
pytest tests/ -q
```

## Support the project

If RAGeval is useful to you, a star on the repository helps other engineers find it, and following [@Yacine-ai-tech](https://github.com/Yacine-ai-tech) is the simplest way to hear about new releases. Passing the link to a colleague who has the same problem is just as welcome.

Questions and field notes go to [Discussions](https://github.com/Yacine-ai-tech/RAGeval/discussions); reproducible bugs go to [Issues](https://github.com/Yacine-ai-tech/RAGeval/issues).

## License

Open-source under the AGPL-3.0 License, free for researchers, students, and open-source use.
AGPLv3 requires that any proprietary network service built on modified RAGeval code also
open-source its backend. A commercial license for closed-source use or enterprise features
such as SSO and custom RBAC is available: see [COMMERCIAL.md](COMMERCIAL.md).

## Anonymous Telemetry

RAGeval sends a single anonymous startup ping, at most once per six hours per running
instance: a timestamp and a randomly generated install identifier, not derived from any
hardware identifier — no API keys, prompts, judge scores, or application data. Destination is
the `TELEMETRY_URL` environment variable; `TELEMETRY_OPT_OUT=true` disables it outright.
