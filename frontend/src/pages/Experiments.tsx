import { useState } from "react";
import { motion } from "framer-motion";
import { Beaker, Trophy, AlertTriangle } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState } from "../kit/primitives";
import { Label } from "../kit/misc";
import { api } from "../lib/api";

/* Both tools call REAL endpoints: /eval/retrieval-bench and /eval/embedding-comparison.
   Input format: one line per query; chunks separated by `;` per line. */

function parseLines(s: string): string[] {
  return s.split("\n").map((l) => l.trim()).filter(Boolean);
}
function parseChunks(s: string): string[][] {
  return parseLines(s).map((l) => l.split(";").map((c) => c.trim()).filter(Boolean));
}

const SAMPLE_Q = "What was Q3 revenue?\nWhich costs increased quarter over quarter?";
const SAMPLE_A = "Q3 revenue was $487.6M, up 18.7% YoY; Gross margin 46.8%\nOperating costs $93.2M, +1.2% QoQ driven by cloud spend";
const SAMPLE_B = "The weather in Q3 was mild; Office relocation completed\nHeadcount grew by 3%; New brand guidelines shipped";

export default function Experiments() {
  return (
    <div>
      <PageHeader
        title="Experiments"
        sub="Side-by-side retrieval strategy benchmarking and embedding-model comparison — the same scorer used in production, run on demand."
      />
      <div className="grid gap-4 xl:grid-cols-2">
        <RetrievalBench />
        <EmbeddingComparison />
      </div>
    </div>
  );
}

function RetrievalBench() {
  const [queries, setQueries] = useState(SAMPLE_Q);
  const [a, setA] = useState(SAMPLE_A);
  const [b, setB] = useState(SAMPLE_B);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [res, setRes] = useState<Awaited<ReturnType<typeof api.retrievalBench>> | null>(null);

  const run = async () => {
    setBusy(true); setErr(""); setRes(null);
    try {
      setRes(await api.retrievalBench(parseLines(queries), parseChunks(a), parseChunks(b)));
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  return (
    <Card title="Retrieval A/B bench" actions={<Chip>one query per line · chunks split by ;</Chip>}>
      <div className="space-y-3">
        <div>
          <Label>Queries</Label>
          <textarea value={queries} onChange={(e) => setQueries(e.target.value)} rows={2} className="num w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 font-mono text-[12px] text-body outline-none focus:border-[var(--accent)]" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <Label>Strategy A chunks</Label>
            <textarea value={a} onChange={(e) => setA(e.target.value)} rows={4} className="num w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 font-mono text-[12px] text-body outline-none focus:border-[var(--accent)]" />
          </div>
          <div>
            <Label>Strategy B chunks</Label>
            <textarea value={b} onChange={(e) => setB(e.target.value)} rows={4} className="num w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 font-mono text-[12px] text-body outline-none focus:border-[var(--accent)]" />
          </div>
        </div>
        <Button onClick={run} disabled={busy}><Beaker size={14} /> {busy ? "Benchmarking…" : "Run bench"}</Button>
        {err && <div className="flex items-start gap-2 text-[13px] text-bad"><AlertTriangle size={14} className="mt-0.5" />{err}</div>}
        {res && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-2 gap-3">
            {(["a", "b"] as const).map((k) => {
              const mean = k === "a" ? res.strategy_a_mean : res.strategy_b_mean;
              const per = k === "a" ? res.per_query_a : res.per_query_b;
              const winner = res.winner === k;
              return (
                <div key={k} className={`rounded-xl border p-4 ${winner ? "border-[var(--accent)]" : "border-line"} bg-surface-2`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium uppercase tracking-wide text-muted">Strategy {k.toUpperCase()}</span>
                    {winner && <Chip tone="accent"><Trophy size={11} /> winner</Chip>}
                  </div>
                  <div className="num mt-1 text-2xl font-bold text-body">{mean.toFixed(3)}</div>
                  <div className="num mt-1 text-[11px] text-muted">per-query: {per.map((p) => p.toFixed(2)).join(" · ")}</div>
                </div>
              );
            })}
          </motion.div>
        )}
      </div>
    </Card>
  );
}

function EmbeddingComparison() {
  const [queries, setQueries] = useState(SAMPLE_Q);
  const [chunks, setChunks] = useState(SAMPLE_A);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [res, setRes] = useState<{ results: Record<string, number>; best: string | null } | null>(null);

  const run = async () => {
    setBusy(true); setErr(""); setRes(null);
    try {
      setRes(await api.embeddingComparison(parseLines(queries), parseChunks(chunks)));
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  return (
    <Card title="Embedding model comparison" actions={<Chip>BGE-large vs MiniLM (server defaults)</Chip>}>
      <div className="space-y-3">
        <div>
          <Label>Queries</Label>
          <textarea value={queries} onChange={(e) => setQueries(e.target.value)} rows={2} className="num w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 font-mono text-[12px] text-body outline-none focus:border-[var(--accent)]" />
        </div>
        <div>
          <Label>Chunks (aligned per query)</Label>
          <textarea value={chunks} onChange={(e) => setChunks(e.target.value)} rows={4} className="num w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 font-mono text-[12px] text-body outline-none focus:border-[var(--accent)]" />
        </div>
        <Button onClick={run} disabled={busy}><Beaker size={14} /> {busy ? "Comparing…" : "Compare embeddings"}</Button>
        {err && <div className="flex items-start gap-2 text-[13px] text-bad"><AlertTriangle size={14} className="mt-0.5" />{err}</div>}
        {res && Object.keys(res.results).length === 0 && (
          <EmptyState title="No results returned" hint="The embedding backend may be unavailable on this deployment." />
        )}
        {res && Object.keys(res.results).length > 0 && (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
            {Object.entries(res.results).map(([model, score]) => (
              <div key={model} className={`flex items-center gap-3 rounded-xl border p-3 ${res.best === model ? "border-[var(--accent)]" : "border-line"} bg-surface-2`}>
                <span className="min-w-0 flex-1 truncate font-mono text-[11.5px] text-dim" title={model}>{model}</span>
                <span className="num text-sm font-bold text-body">{score.toFixed(3)}</span>
                {res.best === model && <Chip tone="accent"><Trophy size={11} /> best</Chip>}
              </div>
            ))}
          </motion.div>
        )}
      </div>
    </Card>
  );
}
