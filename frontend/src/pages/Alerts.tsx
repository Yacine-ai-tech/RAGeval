import { useEffect, useState } from "react";
import { ArrowRight, BellRing, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState, Skeleton } from "../kit/primitives";
import { api, parseFlags, QueryRow } from "../lib/api";

export default function Alerts() {
  const [data, setData] = useState<{ flagged_count: number; alerts: QueryRow[] } | null>(null);
  const [err, setErr] = useState("");

  const load = () => {
    setData(null);
    api.alerts().then(setData).catch((e) => setErr(String(e)));
  };
  useEffect(load, []);

  return (
    <div>
      <PageHeader
        title="Alerts"
        sub="Interactions the evaluation pipeline flagged: low relevance, potential hallucination, judge disagreement, persona scope violations, high latency."
        actions={<Button variant="ghost" onClick={load} aria-label="refresh"><RefreshCw size={14} /></Button>}
      />
      {err && <Card><div className="text-sm text-bad">{err}</div></Card>}
      {!data ? (
        <Skeleton className="h-56 w-full" />
      ) : data.alerts.length === 0 ? (
        <Card>
          <EmptyState icon={BellRing} title="No active alerts" hint="Flagged interactions will appear here the moment a judge disagrees or a threshold is crossed." />
        </Card>
      ) : (
        <div className="space-y-3">
          <div className="text-[13px] text-dim">
            <span className="num font-semibold text-body">{data.flagged_count}</span> flagged total — showing the {data.alerts.length} most recent.{" "}
            <Link to="/queries" className="inline-flex items-center gap-1 underline decoration-dotted hover:text-body">Open full query log <ArrowRight size={12} /></Link>
          </div>
          {data.alerts.map((r) => {
            const flags = parseFlags(r);
            return (
              <Card key={r.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-body">{r.query}</div>
                    <div className="mt-0.5 text-[11.5px] text-muted">
                      {new Date(r.timestamp).toLocaleString()} {r.persona ? `· ${r.persona}` : ""} {r.model ? `· ${r.model}` : ""}
                    </div>
                    {r.answer && <p className="mt-2 line-clamp-2 text-[13px] leading-6 text-dim">{r.answer}</p>}
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-1.5">
                    {flags.map((f) => <Chip key={f} tone="bad">{f.replaceAll("_", " ").toLowerCase()}</Chip>)}
                  </div>
                </div>
                <div className="num mt-3 flex gap-4 text-[12px] text-muted">
                  <span>relevance {r.relevance?.toFixed(2) ?? "—"}</span>
                  <span>groundedness {r.groundedness?.toFixed(2) ?? "—"}</span>
                  <span>faithfulness {r.faithfulness?.toFixed(2) ?? "—"}</span>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
