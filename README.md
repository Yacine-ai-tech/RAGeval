# RAGeval

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![CI](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/omnismart-rageval.svg)](https://pypi.org/project/omnismart-rageval/)

**Drop-in LLMOps Observability Platform for AI Applications**

RAGeval provides self-hosted, research-grade evaluation and observability for Retrieval-Augmented Generation (RAG) and LLM pipelines. It introduces multi-judge consensus scoring, persona-aware evaluation, OpenTelemetry interoperability, and DSPy integration with minimal overhead.

Version: **v0.1.10** | `pip install omnismart-rageval`
> 🔗 **Live dashboard:** https://rageval.ysiddo-ai-projects.app/
> Self-hosting documentation: see [SELF_HOSTING.md](SELF_HOSTING.md).

## The 60-Second Setup

Evaluate interactions in real-time with a single decorator:

```python
from rageval import track

@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def answer_question(query: str, context_chunks: list[str]) -> str:
    ...
```

Access the comprehensive analytics dashboard locally at `http://localhost:8003`.

## Core Capabilities & Metrics

| Metric | Definition |
|--------|------------|
| **Retrieval Relevance** | Cosine similarity between query and retrieved chunks (BGE-large default) |
| **Groundedness Consensus**| Multi-judge LLM scoring (Claude Haiku 4.5 + Groq LLaMA 3.3 + GPT-5-mini), minimizing individual judge bias |
| **Faithfulness** | NLI proxy via per-sentence maximum similarity to any source chunk |
| **Cost & Latency** | Precision tracking of USD expenditures per interaction and end-to-end wall-clock latency |
| **Persona Awareness** | Detects and flags when an agent violates its assigned domain scope |
| **OpenTelemetry (OTel)** | Native export of spans to enterprise APM tools |
| **DSPy Integration** | Log DSPy compile events and optimizer performance directly into the dashboard |

## Competitive Differentiation

| Feature | RAGeval | Phoenix | Langfuse | TruLens |
|---------|---------|---------|----------|---------|
| **Self-Hosted** | ✅ | ✅ | ✅ | ✅ |
| **PostgreSQL Support** | ✅ | ❌ | ❌ | ❌ |
| **Drop-in Decorator** | ✅ | Partial | ❌ | Partial |
| **Persona-Aware RAG** | ✅ | ❌ | ❌ | ❌ |
| **Multi-Judge Consensus**| ✅ | ❌ | ❌ | ❌ |
| **OpenTelemetry Export** | ✅ | ✅ | ✅ | ❌ |
| **Setup Time** | 60 sec | 10 min | 15 min | 10 min |

## Quick Start

```bash
pip install omnismart-rageval     # CLI + import remain `rageval`
rageval init                      # creates ~/.rageval/rageval.db
rageval serve --port 8003
```

## Integration Patterns

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
@track(model="groq/llama-3.3-70b-versatile")
def chain_invoke(query: str, context_chunks: list[str]):
    return chain.invoke({"query": query, "context": context_chunks})
```

## Core API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness and status check |
| POST | `/eval/log` | Compute scores and persist to database |
| POST | `/eval/score` | Compute scores only (no persistence) |
| GET | `/eval/metrics?days=7` | Aggregate dashboard data |
| GET | `/eval/queries` | Retrieve query logs (supports `needs_review` filter) |
| GET | `/eval/cost-report?days=30` | Analytical cost breakdown by day and model |
| POST | `/eval/retrieval-bench` | A/B compare retrieval strategies |
| POST | `/eval/embedding-comparison` | Benchmark embedding models side-by-side |

## Quality & Reliability

Validated by a comprehensive test suite covering API functionality, evaluator consistency, decorator integration, and end-to-end scenarios.

```bash
pytest tests/ -q
```

## Licensing & Commercial Use

RAGeval is open-source under the **AGPL-3.0 License**, ensuring it remains free for researchers, students, and open-source hobbyists.

> **Commercial Use:** The AGPLv3 license mandates that any proprietary network service (e.g., SaaS, internal corporate tools) using or modifying this codebase must open-source its entire backend.
> 
> If you require integration into a closed-source commercial environment or need **Enterprise features** (e.g., SSO, VPC Deployment, Strict RBAC, PostgreSQL optimizations), you must obtain a **Commercial License**. See [COMMERCIAL.md](COMMERCIAL.md) for details.

## 📡 Anonymous Telemetry
This project collects anonymous, GDPR-compliant startup pings to help understand usage volume and prioritize development.
* **Data Collected:** Startup event timestamp and anonymized deployment origin. No API keys, prompts, or sensitive data are collected.
* **Opt-Out:** Set `TELEMETRY_OPT_OUT=true` in your `.env` file.

See [TELEMETRY.md](TELEMETRY.md) for detailed privacy practices.

<!-- Project Analytics -->
<img src="https://gateway.ysiddo-ai-projects.app/pixel/RAGeval" width="1" height="1" style="display:none;" alt="">
