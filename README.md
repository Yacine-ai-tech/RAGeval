# RAGeval

[![CI](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/omnismart-rageval.svg)](https://pypi.org/project/omnismart-rageval/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

**Self-hosted LLMOps observability for RAG pipelines, with multi-judge consensus scoring,
persona-scope detection, and a drop-in Python decorator.**

`pip install omnismart-rageval` (v0.2.1)

**Live demo:** https://rageval.ysiddo-ai-projects.app/ — score a query and inspect metrics
directly in the browser dashboard, or drive the same functionality via the `/eval/*` API.
Self-hosting instructions: [SELF_HOSTING.md](SELF_HOSTING.md).

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
| Setup time | ~1 minute | ~10 minutes | ~15 minutes | ~10 minutes |

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

## Tests

70+ test functions across smoke, API, evaluator, decorator, DSPy integration, storage, and
end-to-end paths:

```bash
pytest tests/ -q
```

## License

Open-source under the AGPL-3.0 License, free for researchers, students, and open-source use.
AGPLv3 requires that any proprietary network service built on modified RAGeval code also
open-source its backend. A commercial license — for closed-source use or enterprise features
such as SSO and custom RBAC — is available: see [COMMERCIAL.md](COMMERCIAL.md).

## Anonymous Telemetry

RAGeval sends a single anonymous startup ping, at most once per six hours per running
instance: a timestamp and a randomly generated install identifier, not derived from any
hardware identifier — no API keys, prompts, judge scores, or application data. Destination is
the `TELEMETRY_URL` environment variable; `TELEMETRY_OPT_OUT=true` disables it outright.
