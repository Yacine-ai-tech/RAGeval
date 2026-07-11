import { useState } from "react";
import { motion } from "framer-motion";
import { Bookmark, Check, FlaskConical, Save, AlertTriangle, Scale, UserRoundCheck } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState } from "../kit/primitives";
import { ExecutionStages, Label } from "../kit/misc";
import { JSONViewer } from "../kit/JSONViewer";
import { api, saveEval, Scores, scoreTone } from "../lib/api";

const SAMPLE = {
  query: "What was Q3 revenue and how did gross margin move?",
  answer:
    "Q3 revenue was $487.6M, up 18.7% year over year. Gross margin expanded to 46.8% from 43.1% in Q2, driven by improved product mix and lower logistics costs.",
  chunks:
    "Q3 FY2025 revenue: $487.6M (+12.4% QoQ, +18.7% YoY).\n---\nGross margin Q3: 46.8% vs 43.1% in Q2; drivers: product mix, pricing discipline, logistics costs.\n---\nOperating costs were flat at $93.2M (+1.2% QoQ).",
};

export default function Evaluate() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [chunks, setChunks] = useState("");
  const [persona, setPersona] = useState("");
  const [busy, setBusy] = useState(false);
  const [logged, setLogged] = useState(false);
  const [saved2, setSaved2] = useState(false);
  const [result, setResult] = useState<Scores | null>(null);
  const [err, setErr] = useState("");

  const payload = () => ({
    query,
    answer,
    chunks: chunks.split(/\n---\n?|\n\n/).map((c) => c.trim()).filter(Boolean),
    persona: persona.trim() || null,
    model: "manual/evaluate-page",
  });

  const run = async () => {
    setBusy(true); setErr(""); setResult(null); setLogged(false);
    try {
      setResult(await api.score(payload()));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  };

  const logIt = async () => {
    setBusy(true);
    try { await api.log(payload()); setLogged(true); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader
        title="Evaluate"
        sub="Score any query + answer + retrieved context through the real evaluation pipeline: relevance, multi-judge groundedness consensus, faithfulness, persona scope."
        actions={
          <Button variant="secondary" onClick={() => { setQuery(SAMPLE.query); setAnswer(SAMPLE.answer); setChunks(SAMPLE.chunks); setPersona("cfo"); }}>
            Use sample input
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Interaction">
          <div className="space-y-4">
            <div>
              <Label>User query</Label>
              <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={2} className="w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 text-sm text-body outline-none focus:border-[var(--accent)]" />
            </div>
            <div>
              <Label>LLM answer</Label>
              <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={4} className="w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 text-sm text-body outline-none focus:border-[var(--accent)]" />
            </div>
            <div>
              <Label>Retrieved chunks (separate with --- or blank line)</Label>
              <textarea value={chunks} onChange={(e) => setChunks(e.target.value)} rows={5} className="num w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 font-mono text-[12.5px] text-body outline-none focus:border-[var(--accent)]" />
            </div>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Label>Persona (optional — enables scope checking)</Label>
                <input value={persona} onChange={(e) => setPersona(e.target.value)} placeholder="cfo, chro, coo…" className="w-full rounded-input border border-line-strong bg-surface-2 px-3 py-2 text-sm text-body outline-none focus:border-[var(--accent)]" />
              </div>
              <Button onClick={run} disabled={busy || !query || !answer}>
                <FlaskConical size={14} /> {busy ? "Scoring…" : "Score"}
              </Button>
            </div>
          </div>
        </Card>

        <Card
          title="Evaluation result"
          actions={
            result && (
              <div className="flex items-center gap-2">
                <Button variant="secondary" onClick={() => { saveEval({ ts: Date.now(), label: query.slice(0, 70) || "evaluation", payload: payload(), scores: result }); setSaved2(true); setTimeout(() => setSaved2(false), 1400); }}>
                  {saved2 ? <Check size={13} className="text-ok" /> : <Bookmark size={13} />} {saved2 ? "Saved" : "Save"}
                </Button>
                <Button variant="secondary" onClick={logIt} disabled={busy || logged}>
                  {logged ? <Check size={13} className="text-ok" /> : <Save size={13} />} {logged ? "Logged" : "Log interaction"}
                </Button>
              </div>
            )
          }
        >
          {busy && !result ? (
            <ExecutionStages stages={["Embedding query & chunks", "Running judge panel", "Computing consensus", "Checking persona scope"]} active={1} />
          ) : err ? (
            <div className="flex items-start gap-3"><AlertTriangle size={16} className="mt-0.5 text-bad" /><div className="text-[13px] text-dim">{err}</div></div>
          ) : !result ? (
            <EmptyState icon={Scale} title="No evaluation yet" hint="Fill the interaction on the left (or load the sample input) and run the real scoring pipeline." />
          ) : (
            <ResultView r={result} />
          )}
        </Card>
      </div>
    </div>
  );
}

function Dim({ label, v }: { label: string; v: number }) {
  const tone = scoreTone(v);
  const color = tone === "ok" ? "var(--success)" : tone === "warn" ? "var(--warning)" : "var(--danger)";
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-3.5">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="num mt-1 text-xl font-bold" style={{ color }}>{v.toFixed(2)}</div>
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-bg">
        <motion.div className="h-full rounded-full" style={{ background: color }} initial={{ width: 0 }} animate={{ width: `${v * 100}%` }} />
      </div>
    </div>
  );
}

function ResultView({ r }: { r: Scores }) {
  const c = r.groundedness_consensus;
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Dim label="Relevance" v={r.relevance} />
        <Dim label="Groundedness" v={r.groundedness} />
        <Dim label="Faithfulness" v={r.faithfulness} />
        <Dim label="Overall" v={r.overall_quality} />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wide text-muted">Multi-judge consensus</span>
          {c.flag_for_review ? <Chip tone="bad">judge disagreement — human review</Chip> : <Chip tone="ok">judges agree</Chip>}
        </div>
        {c.judges.length === 0 ? (
          <div className="rounded-xl border border-line bg-surface-2 p-3.5 text-[13px] text-dim">
            No judge providers are configured on this deployment; the consensus reflects zero recorded votes.
          </div>
        ) : (
          <div className="grid gap-2 sm:grid-cols-3">
            {c.judges.map((j) => (
              <div key={j.model} className="rounded-xl border border-line bg-surface-2 p-3">
                <div className="truncate font-mono text-[11px] text-muted" title={j.model}>{j.model}</div>
                <div className="num mt-1 text-lg font-bold text-body">{j.score.toFixed(2)}</div>
              </div>
            ))}
          </div>
        )}
        <div className="num mt-2 text-[11.5px] text-muted">
          consensus {c.consensus.toFixed(3)} · σ {c.stdev.toFixed(3)} · {c.judges_used} judge{c.judges_used === 1 ? "" : "s"} voted
        </div>
      </div>

      {r.persona && (
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted">
            <UserRoundCheck size={13} /> Persona scope — {r.persona}
          </div>
          {r.persona_scope_violations.length === 0 ? (
            <Chip tone="ok">no scope violations</Chip>
          ) : (
            <div className="space-y-1.5">
              {r.persona_scope_violations.map((v, i) => (
                <div key={i} className="rounded-xl border border-line bg-[rgba(255,107,107,0.06)] p-3 text-[13px] text-dim">
                  {typeof v === "string" ? v : JSON.stringify(v)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        {r.flags.map((f) => <Chip key={f} tone="bad">{f}</Chip>)}
        <Chip className="num">${r.cost_usd.toFixed(5)}</Chip>
        <Chip className="num">{Math.round(r.latency_ms)} ms</Chip>
      </div>

      <JSONViewer data={r} maxHeight={260} />
    </motion.div>
  );
}
