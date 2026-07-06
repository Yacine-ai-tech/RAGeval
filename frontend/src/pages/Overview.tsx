import { useEffect, useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Activity, ArrowRight, CircleDollarSign, Clock3, Database, Flag, Target, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip, EmptyState, Skeleton, StatTile } from "../kit/primitives";
import { Select } from "../kit/misc";
import { api, Metrics, QueryRow } from "../lib/api";

export default function Overview() {
  const [days, setDays] = useState("7");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [rows, setRows] = useState<QueryRow[] | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    setMetrics(null);
    Promise.all([api.metrics(Number(days)), api.queries(200)])
      .then(([m, q]) => { setMetrics(m); setRows(q); })
      .catch((e) => setErr(String(e)));
  }, [days]);

  // The API's query_volume_by_hour is always empty (GAP_REPORT §2) — build the quality
  // trend client-side from real query-log timestamps instead.
  const trend = useMemo(() => {
    if (!rows) return [];
    const sorted = [...rows].reverse(); // oldest → newest
    return sorted.map((r, i) => ({
      i: i + 1,
      label: new Date(r.timestamp).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      relevance: r.relevance,
      groundedness: r.groundedness,
      faithfulness: r.faithfulness,
    }));
  }, [rows]);

  return (
    <div>
      <PageHeader
        title="Overview"
        sub="Quality, cost and reliability of every tracked RAG interaction, scored by the multi-judge evaluation pipeline."
        actions={
          <Select
            value={days}
            onChange={setDays}
            options={[{ value: "7", label: "Last 7 days" }, { value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }]}
          />
        }
      />

      {err && <Card><div className="text-sm text-bad">{err}</div></Card>}

      {!metrics ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile label="Tracked queries" value={metrics.total_queries} icon={Database} sub={`last ${days} days`} />
            <StatTile
              label="Avg retrieval relevance"
              value={metrics.avg_relevance.toFixed(2)}
              icon={Target}
              delta={{ text: metrics.avg_relevance >= 0.75 ? "healthy" : "below threshold", good: metrics.avg_relevance >= 0.75 }}
            />
            <StatTile
              label="Avg groundedness"
              value={metrics.avg_groundedness.toFixed(2)}
              icon={ShieldCheck}
              delta={{ text: metrics.avg_groundedness >= 0.75 ? "healthy" : "review", good: metrics.avg_groundedness >= 0.75 }}
            />
            <StatTile
              label="Flagged for review"
              value={metrics.flagged_count}
              icon={Flag}
              delta={metrics.flagged_count > 0 ? { text: "needs attention", good: false } : { text: "all clear" }}
            />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <StatTile label="Avg faithfulness" value={metrics.avg_faithfulness.toFixed(2)} icon={Activity} />
            <StatTile label="Avg latency" value={`${Math.round(metrics.avg_latency_ms)} ms`} icon={Clock3} />
            <StatTile label="Total cost" value={`$${metrics.total_cost_usd.toFixed(4)}`} icon={CircleDollarSign} sub={`last ${days} days`} />
          </div>
        </>
      )}

      <Card
        title="Quality per tracked query"
        className="mt-5"
        actions={<Chip title="derived client-side from the real query log">query log</Chip>}
      >
        {trend.length === 0 ? (
          <EmptyState
            title="No tracked interactions yet"
            hint="Score one on the Evaluate page or instrument your RAG app with the @track decorator."
            action={<Link className="text-sm underline decoration-dotted text-dim hover:text-body" to="/evaluate" style={{display:"inline-flex",alignItems:"center",gap:4}}>Open Evaluate <ArrowRight size={12} /></Link>}
          />
        ) : (
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
                <CartesianGrid stroke="var(--grid-line)" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={{ stroke: "var(--border)" }} tickLine={false} minTickGap={40} />
                <YAxis domain={[0, 1]} tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border-strong)", borderRadius: 12, color: "var(--text)", fontSize: 12 }}
                  formatter={(v) => [typeof v === "number" ? v.toFixed(3) : "—"]}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-2)" }} />
                <Line type="monotone" dataKey="relevance" stroke="var(--accent)" dot={false} strokeWidth={2} isAnimationActive={false} />
                <Line type="monotone" dataKey="groundedness" stroke="var(--accent-2)" dot={false} strokeWidth={2} isAnimationActive={false} />
                <Line type="monotone" dataKey="faithfulness" stroke="var(--success)" dot={false} strokeWidth={1.5} strokeDasharray="4 3" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
    </div>
  );
}
