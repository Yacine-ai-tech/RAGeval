# RAGeval

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)


[![CI](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml/badge.svg)](https://github.com/Yacine-ai-tech/RAGeval/actions/workflows/ci.yml) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

[![PyPI](https://img.shields.io/pypi/v/omnismart-rageval.svg)](https://pypi.org/project/omnismart-rageval/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

**Drop-in LLMOps observability. Self-hosted. SQLite-default. Persona-aware. Multi-judge consensus.**
> 🔗 **Live dashboard:** https://rageval.ysiddo-ai-projects.app/  ·  browser dashboard (score a query + view metrics).  Also fully scriptable — **API:** `/health`, `/eval/*` via `curl`/HTTPie.
> On-demand backend (first request ~30–60 s to wake).
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
pip install omnismart-rageval     # distribution name; CLI + import remain `rageval`
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

AGPL-3.0

## ⚖️ License & Enterprise Use (Dual-License)

This project is open-source under the **AGPL-3.0 License**. It is completely free for researchers, students, and open-source hobbyists.

> **Commercial Use:** The AGPLv3 license requires that any proprietary network service (SaaS, internal corporate tools) that uses or modifies this code must also open-source its entire backend. 
> 
> If you wish to use this framework in a closed-source commercial environment, or require **Enterprise features** (SSO, Active Directory, Custom VPC Deployment, Strict RBAC), you must obtain a **Commercial License**. 
> Please reach out to discuss commercial licensing and integration consulting.

## 📡 Anonymous Telemetry
This project collects anonymous, GDPR-compliant startup pings to help the author understand usage volume and prioritize development. 
* **What is collected:** A startup event timestamp and anonymized deployment origin. No API keys, no user prompts, and no sensitive application data is ever collected.
* **How to disable:** We respect your privacy and development environment. To opt-out, simply set `TELEMETRY_OPT_OUT=true` in your `.env` file.


<!-- Project Analytics -->
<img referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=a8deecd4-e42d-4498-a1b0-208aacf89a40" />

## Licensing
This project is licensed under the [AGPL-3.0 License](LICENSE).

**Commercial Use:** If you wish to use this software commercially without releasing your own source code, please see [COMMERCIAL.md](COMMERCIAL.md) to obtain a commercial license.

**Telemetry:** See [TELEMETRY.md](TELEMETRY.md) for our privacy-first data practices.
