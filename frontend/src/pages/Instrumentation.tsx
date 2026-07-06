import { useState } from "react";
import { Check, Copy, Package, Puzzle } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip } from "../kit/primitives";

/* All snippets are the REAL public API of the published package (README-verified):
   pip install omnismart-rageval · from rageval import track */

const SNIPPETS: { title: string; tag: string; code: string }[] = [
  {
    title: "One decorator — any RAG function",
    tag: "core",
    code: `pip install omnismart-rageval

from rageval import track

@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def answer(query: str):
    chunks = await retriever.search(query)
    return await llm.generate(query, chunks=chunks)`,
  },
  {
    title: "FastAPI",
    tag: "framework",
    code: `from rageval import track

@app.post("/ask")
@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def ask(query: str):
    chunks = await retriever.search(query)
    return await llm.generate(query, chunks=chunks)`,
  },
  {
    title: "LangChain",
    tag: "framework",
    code: `from rageval import track

@track(model="groq/llama-3.3-70b-versatile")
def chain_invoke(query: str, context_chunks: list[str]):
    return chain.invoke({"query": query, "context": context_chunks})`,
  },
  {
    title: "HTTP API (no SDK)",
    tag: "rest",
    code: `curl -X POST $RAGEVAL_URL/eval/log \\
  -H 'Content-Type: application/json' \\
  -d '{
    "query": "What was Q3 revenue?",
    "answer": "Q3 revenue was $487.6M...",
    "chunks": ["Q3 FY2025 revenue: $487.6M ..."],
    "model": "anthropic/claude-sonnet-4-6",
    "persona": "cfo"
  }'`,
  },
];

export default function Instrumentation() {
  return (
    <div>
      <PageHeader
        title="Instrumentation"
        sub="Self-hosted observability with one decorator. Every call is scored for relevance, multi-judge groundedness, faithfulness and persona scope — then lands in this dashboard."
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <Chip tone="accent"><Package size={11} /> omnismart-rageval on PyPI</Chip>
        <Chip><Puzzle size={11} /> import name stays `rageval`</Chip>
        <Chip>zero vendor lock-in — your DB, your judges</Chip>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {SNIPPETS.map((s) => <Snippet key={s.title} {...s} />)}
      </div>
    </div>
  );
}

function Snippet({ title, tag, code }: { title: string; tag: string; code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Card
      title={title}
      actions={
        <div className="flex items-center gap-2">
          <Chip>{tag}</Chip>
          <button
            className="flex items-center gap-1 rounded-lg border border-line px-2 py-1 text-[11px] text-dim hover:text-body"
            onClick={() => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
          >
            {copied ? <Check size={11} className="text-ok" /> : <Copy size={11} />} {copied ? "Copied" : "Copy"}
          </button>
        </div>
      }
    >
      <pre className="num overflow-x-auto rounded-xl border border-line bg-bg p-4 font-mono text-[12px] leading-6 text-dim">{code}</pre>
    </Card>
  );
}
