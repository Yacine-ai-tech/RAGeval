import { useEffect, useState } from "react";
import { Scale, Cpu, ShieldAlert, Gauge } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip, Skeleton } from "../kit/primitives";
import { api, EvalConfig } from "../lib/api";

/* v1 "Models" — the real judge panel and embedding model from /eval/config, plus the
   scoring dimensions and review flags the evaluator actually emits. */

const DIMS = [
  { name: "Retrieval relevance", desc: "Query-to-chunk similarity over the retrieved context." },
  { name: "Groundedness", desc: "Multi-judge consensus: is the answer supported by the context?" },
  { name: "Faithfulness", desc: "Sentence-level entailment of claims against the chunks." },
  { name: "Latency", desc: "End-to-end response time, flagged past threshold." },
  { name: "Cost", desc: "Token spend per interaction, aggregated per model." },
];

export default function Models() {
  const [cfg, setCfg] = useState<EvalConfig | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.config().then(setCfg).catch((e) => setErr(String(e))); }, []);

  return (
    <div>
      <PageHeader
        title="Models & evaluators"
        sub="The judge panel, embedding model and scoring configuration this deployment actually runs — read live from the server."
      />
      {err && <Card><div className="text-sm text-bad">{err}</div></Card>}
      {!cfg ? (
        <Skeleton className="h-56 w-full" />
      ) : (
        <>
          <Card title={<span className="flex items-center gap-2"><Scale size={15} /> Judge panel</span>}
            actions={<Chip>{cfg.judge_models.length} configured</Chip>}>
            <p className="mb-3 text-[13px] leading-6 text-dim">
              Groundedness is scored by multiple judges in parallel; unreachable providers are skipped so the
              consensus reflects only real votes. Disagreement above σ&nbsp;
              <span className="num">{cfg.disagreement_stdev_threshold}</span> raises a human-review flag.
            </p>
            <div className="grid gap-2 sm:grid-cols-3">
              {cfg.judge_models.map((m) => (
                <div key={m} className="rounded-xl border border-line bg-surface-2 p-3">
                  <Cpu size={14} className="text-dim" />
                  <div className="num mt-2 break-all font-mono text-[11.5px] text-body">{m}</div>
                </div>
              ))}
            </div>
          </Card>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card title={<span className="flex items-center gap-2"><Gauge size={15} /> Embedding model</span>}>
              <div className="num break-all font-mono text-[13px] text-body">{cfg.embedding_model ?? "—"}</div>
              <p className="mt-2 text-[13px] leading-6 text-dim">
                Powers retrieval-relevance scoring and the embedding-comparison experiment.
              </p>
            </Card>
            <Card title={<span className="flex items-center gap-2"><ShieldAlert size={15} /> Review flags</span>}>
              <div className="flex flex-wrap gap-1.5">
                {cfg.review_flags.map((f) => <Chip key={f} tone="warn">{f}</Chip>)}
              </div>
              <p className="mt-3 text-[13px] leading-6 text-dim">Any of these on an interaction marks it for human review.</p>
            </Card>
          </div>

          <Card title="Scoring dimensions" className="mt-4">
            <div className="divide-y divide-[var(--border)]">
              {DIMS.map((d) => (
                <div key={d.name} className="flex items-baseline gap-4 py-2.5">
                  <span className="w-44 shrink-0 text-[13px] font-semibold text-body">{d.name}</span>
                  <span className="text-[13px] leading-6 text-dim">{d.desc}</span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
