# RAGeval

[![CI](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![PyPI](https://img.shields.io/pypi/v/rageval.svg)](https://pypi.org/project/rageval/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Drop-in LLMOps observability. Self-hosted. SQLite-default. Persona-aware. Multi-judge consensus.**

## The 60-Second Pitch

```python
from rageval import track

@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def answer_question(query: str, context_chunks: list[str]) -> str:
    ...
```

That's it. Open the dashboard at `localhost:8003`.

## What It Measures

| Metric            | Definition                                                          |
|-------------------|---------------------------------------------------------------------|
| Retrieval relevance | Cosine sim between query and retrieved chunks (BGE-large by default) |
| Groundedness consensus | Multi-judge LLM scoring (Claude Haiku + Groq Llama + GPT-5-mini), flags disagreement |
| Faithfulness      | Per-sentence max-similarity to any chunk (NLI proxy)                |
| Cost              | USD per interaction, tracked by model                               |
| Latency           | End-to-end wall-clock                                               |

## Comparison vs Alternatives

| Feature             | RAGeval  | Phoenix  | Langfuse | TruLens  |
|---------------------|----------|----------|----------|----------|
| Self-hosted         | ✅       | ✅        | ✅        | ✅        |
| SQLite default      | ✅       | ❌        | ❌        | ❌        |
| Drop-in decorator   | ✅       | partial   | ❌        | partial   |
| Persona-aware       | ✅       | ❌        | ❌        | ❌        |
| Multi-judge consensus | ✅     | ❌        | ❌        | ❌        |
| Cost tracking       | ✅       | ✅        | ✅        | partial   |
| Setup time          | 60 sec   | 10 min    | 15 min    | 10 min    |

## Quick Start

```bash
pip install rageval
rageval init                 # creates ~/.rageval/rageval.db
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
@track(model="groq/llama-3.3-70b-versatile")
def chain_invoke(query: str, context_chunks: list[str]):
    return chain.invoke({"query": query, "context": context_chunks})
```

## Endpoints

| Method | Path                          | Purpose                                  |
|--------|-------------------------------|------------------------------------------|
| GET    | /health                       | Liveness                                 |
| POST   | /eval/log                     | Score + store                            |
| POST   | /eval/score                   | Score only (no storage)                  |
| GET    | /eval/metrics?days=7          | Aggregate dashboard data                 |
| GET    | /eval/queries                 | Query log (filter by needs_review)       |
| GET    | /eval/cost-report?days=30     | Cost breakdown by day + model            |
| GET    | /eval/alerts                  | Recent flagged queries                   |
| POST   | /eval/retrieval-bench         | A/B compare retrieval strategies         |
| POST   | /eval/embedding-comparison    | Compare embedding models                 |

## License

MIT
