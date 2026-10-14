import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity, BookOpen, Boxes, Database, Gauge, GitBranch, Layers, Pause, Play, RadioTower,
  Scale, ShieldCheck, Sigma, Sparkles, Workflow,
} from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip } from "../kit/primitives";
import { PipelineFlow, type Stage } from "../kit/PipelineFlow";

type NodeInfo = { id: string; label: string; layer: string; icon: typeof Boxes; summary: string; detail: string[]; env?: string[] };

const LAYERS = ["Ingress", "Scoring", "Persistence", "Surfaces"] as const;

const NODES: NodeInfo[] = [
  { id: "decorator", label: "@track decorator", layer: "Ingress", icon: Workflow,
    summary: "Wraps your sync or async RAG function and scores it in the background.",
    detail: ["Your function's return value is never delayed; scoring is scheduled on the running event loop or a dedicated background loop.", "flush() waits for pending evaluations in short-lived scripts."] },
  { id: "api", label: "REST API", layer: "Ingress", icon: GitBranch,
    summary: "POST /eval/log and /eval/score with optional shared-token auth.",
    detail: ["Rate-limited write routes, bounded request bodies and a bounded number of concurrent evaluations.", "Reads are scoped to the visitor's session unless an admin token is presented."],
    env: ["REQUIRE_INTERNAL_TOKEN", "RAGEVAL_MAX_REQUEST_BODY_BYTES", "RAGEVAL_MAX_CONCURRENT_EVALUATIONS", "DEMO_SESSION_SCOPING"] },
  { id: "relevance", label: "Retrieval relevance", layer: "Scoring", icon: Gauge,
    summary: "Embedding similarity between the query and every retrieved chunk.",
    detail: ["Backend is chosen explicitly: in-process model, remote endpoint, or a lexical fallback.", "The embedder is warmed at startup so the first request does not pay for model load."],
    env: ["USE_LOCAL_EMBEDDER", "INFERENCE_MODE", "EMBEDDING_ENDPOINT", "EMBEDDING_MODEL"] },
  { id: "panel", label: "Judge panel", layer: "Scoring", icon: Scale,
    summary: "Independent LLM judges from different providers rate groundedness.",
    detail: ["At least two judges must answer; there is no single-judge fallback.", "Scores are combined with accuracy-based weights (weighted mean or median); disagreement flags the record for review.", "A key pool rotates provider keys and parks a rate-limited key until its retry window ends."],
    env: ["JUDGE_MODELS", "LLM_JUDGE_FALLBACK", "JUDGE_TIMEOUT", "RAGEVAL_AGGREGATION_STRATEGY", "RAGEVAL_INCLUDE_SYMBOLIC_JUDGE"] },
  { id: "faith", label: "Faithfulness", layer: "Scoring", icon: Sigma,
    summary: "Per-sentence best similarity to any retrieved chunk (an NLI proxy).",
    detail: ["Catches answers that drift from the evidence even when overall relevance is high."] },
  { id: "store", label: "Store", layer: "Persistence", icon: Database,
    summary: "SQLite by default, Postgres with pgvector for production.",
    detail: ["Idempotent schema bootstrap; a migration error stops startup.", "With Postgres the query embedding is stored in a vector column for similarity queries."],
    env: ["RAGEVAL_STORE", "RAGEVAL_DB_PATH", "RAGEVAL_POSTGRES_URL", "RAGEVAL_EMBEDDING_DIM"] },
  { id: "dash", label: "Dashboard", layer: "Surfaces", icon: Layers,
    summary: "Overview, queries, live traces, cost, alerts, models and experiments.",
    detail: ["Live traces use a WebSocket feed with a polling fallback."] },
  { id: "otel", label: "OpenTelemetry", layer: "Surfaces", icon: RadioTower,
    summary: "Optional OTLP span export for existing observability stacks.",
    detail: ["Enabled when an endpoint is configured; absent otherwise."], env: ["RAGEVAL_OTEL_ENDPOINT"] },
];

const STAGES: (Stage & { text: string; nodes: string[] })[] = [
  { id: "admit", label: "Admit", icon: ShieldCheck, text: "Authenticate, rate-limit, validate sizes, resolve the visitor session and take an evaluation slot.", nodes: ["api"] },
  { id: "fanout", label: "Score in parallel", icon: Activity, text: "Relevance, groundedness consensus and faithfulness run concurrently; all three finish before errors are raised.", nodes: ["relevance", "panel", "faith"] },
  { id: "combine", label: "Combine", icon: Sparkles, text: "Overall quality = 0.4 relevance + 0.4 groundedness + 0.2 faithfulness; cost and flags are derived.", nodes: ["panel"] },
  { id: "persist", label: "Persist", icon: Database, text: "The record is written to the store, with the query embedding when Postgres is used.", nodes: ["store"] },
  { id: "publish", label: "Publish", icon: RadioTower, text: "Live subscribers and exporters receive the event; the dashboard aggregates it.", nodes: ["dash", "otel"] },
];

export default function ArchitecturePage() {
  const [selected, setSelected] = useState<string>("panel");
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setStep((s) => (s + 1) % (STAGES.length + 1)), 1800);
    return () => clearInterval(t);
  }, [playing]);

  const current = STAGES[Math.min(step, STAGES.length - 1)];
  const highlighted = useMemo(() => new Set(step < STAGES.length ? current.nodes : []), [step, current]);
  const node = NODES.find((n) => n.id === selected) ?? NODES[0];

  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto space-y-8">
      <PageHeader
        title="Architecture"
        sub="How one (query, answer, chunks) interaction becomes a scored, persisted and queryable record."
        actions={
          <div className="flex gap-2">
            <Link to="/research"><Button variant="secondary"><BookOpen size={14} className="mr-1 inline" /> Research</Button></Link>
            <Link to="/benchmark"><Button variant="secondary"><Scale size={14} className="mr-1 inline" /> Benchmark</Button></Link>
          </div>
        }
      />

      <Card title="Request lifecycle">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs text-dim">Select a stage or let it play. Highlighted components below are the ones involved.</div>
          <Button variant="secondary" onClick={() => setPlaying((p) => !p)}>
            {playing ? <Pause size={14} className="mr-1 inline" /> : <Play size={14} className="mr-1 inline" />}
            {playing ? "Pause" : "Play"}
          </Button>
        </div>
        <PipelineFlow stages={STAGES} active={step} done={step >= STAGES.length} />
        <div className="mt-3 flex flex-wrap gap-2">
          {STAGES.map((s, i) => (
            <button key={s.id} onClick={() => { setPlaying(false); setStep(i); }}
              className={`rounded-lg border px-3 py-1 text-xs ${i === step ? "border-accent text-body" : "border-line text-dim"}`}>
              {i + 1}. {s.label}
            </button>
          ))}
        </div>
        <p className="mt-3 text-sm text-dim">{step < STAGES.length ? current.text : "Done: the record is stored and visible in the dashboard."}</p>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {LAYERS.map((layer) => (
            <Card key={layer} title={layer}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {NODES.filter((n) => n.layer === layer).map((n) => {
                  const Icon = n.icon;
                  const active = selected === n.id;
                  const lit = highlighted.has(n.id);
                  return (
                    <button key={n.id} onClick={() => setSelected(n.id)}
                      className={`text-left rounded-xl border p-3 transition-colors ${active ? "border-accent bg-surface-2" : "border-line bg-surface"} ${lit ? "ring-1 ring-accent" : ""}`}>
                      <div className="flex items-center gap-2 text-sm font-semibold text-body"><Icon size={14} /> {n.label}</div>
                      <div className="mt-1 text-xs text-dim">{n.summary}</div>
                    </button>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>

        <Card title={node.label} className="h-fit lg:sticky lg:top-4">
          <p className="text-sm text-dim">{node.summary}</p>
          <ul className="mt-3 space-y-2 text-xs text-dim list-disc pl-4">
            {node.detail.map((d) => <li key={d}>{d}</li>)}
          </ul>
          {node.env && (
            <div className="mt-4">
              <div className="text-[11px] uppercase tracking-wider text-muted mb-1">Configuration</div>
              <div className="flex flex-wrap gap-1.5">{node.env.map((e) => <Chip key={e}>{e}</Chip>)}</div>
            </div>
          )}
        </Card>
      </div>

      <Card title="Design decisions">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-dim">
          {[
            ["Heterogeneous panel", "Judges from different providers avoid correlated errors; an outage in one family does not stop scoring."],
            ["No silent downgrade", "Fewer than two judges is an error, not a one-judge 'consensus'. The embedding backend is also never swapped silently."],
            ["Off the critical path", "Scoring is scheduled in the background so instrumenting an app never adds latency to its answers."],
          ].map(([t, d]) => (
            <div key={t} className="rounded-xl border border-line bg-surface-2 p-4">
              <div className="font-semibold text-body text-sm mb-1">{t}</div>{d}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
