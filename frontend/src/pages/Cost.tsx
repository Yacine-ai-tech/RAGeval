import { useEffect, useMemo, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { CircleDollarSign } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, EmptyState, Skeleton, StatTile } from "../kit/primitives";
import { Select } from "../kit/misc";
import { api, CostReport } from "../lib/api";

export default function Cost() {
  const [days, setDays] = useState("30");
  const [report, setReport] = useState<CostReport | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    setReport(null);
    api.costReport(Number(days)).then(setReport).catch((e) => setErr(String(e)));
  }, [days]);

  const daily = useMemo(() => {
    if (!report) return [];
    const d = report.daily_costs;
    if (Array.isArray(d)) return d.map((x) => ({ day: x.day, cost: x.cost }));
    return Object.entries(d ?? {}).map(([day, cost]) => ({ day, cost: cost as number }));
  }, [report]);

  const byModel = useMemo(
    () => Object.entries(report?.by_model ?? {}).sort(([, a], [, b]) => (b as number) - (a as number)),
    [report],
  );

  return (
    <div>
      <PageHeader
        title="Cost intelligence"
        sub="Real evaluation-pipeline spend per day and per model, from the persisted query log."
        actions={
          <Select value={days} onChange={setDays} options={[{ value: "7", label: "7 days" }, { value: "30", label: "30 days" }, { value: "90", label: "90 days" }]} />
        }
      />

      {err && <Card><div className="text-sm text-bad">{err}</div></Card>}
      {!report ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatTile label="Total cost" value={`$${report.total_cost_usd.toFixed(4)}`} icon={CircleDollarSign} sub={`last ${report.days} days`} />
            <StatTile label="Models billed" value={byModel.length} sub="with tracked spend" />
            <StatTile
              label="Top model"
              value={byModel[0] ? byModel[0][0].split("/").pop() : "—"}
              sub={byModel[0] ? `$${(byModel[0][1] as number).toFixed(4)}` : "no spend yet"}
            />
          </div>

          <Card title="Daily cost" className="mt-5">
            {!Array.isArray(daily) || daily.length === 0 ? (
              <EmptyState title="No cost data yet" hint="Costs accumulate as interactions are logged with token usage." />
            ) : (
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={daily} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
                    <defs>
                      <linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--grid-line)" vertical={false} />
                    <XAxis dataKey="day" tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={{ stroke: "var(--border)" }} tickLine={false} minTickGap={30} />
                    <YAxis tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} />
                    <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border-strong)", borderRadius: 12, color: "var(--text)", fontSize: 12 }} formatter={(v: number) => [`$${v.toFixed(5)}`, "cost"]} />
                    <Area type="monotone" dataKey="cost" stroke="var(--accent)" strokeWidth={2} fill="url(#costFill)" isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          <Card title="Spend by model" className="mt-5">
            {byModel.length === 0 ? (
              <EmptyState title="No per-model spend yet" />
            ) : (
              <div className="space-y-2.5">
                {byModel.map(([model, cost]) => {
                  const max = byModel[0][1] as number;
                  return (
                    <div key={model} className="flex items-center gap-3">
                      <span className="w-56 shrink-0 truncate font-mono text-[11.5px] text-dim" title={model}>{model}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                        <div className="h-full rounded-full" style={{ width: `${Math.max(4, ((cost as number) / max) * 100)}%`, background: "var(--accent-grad)" }} />
                      </div>
                      <span className="num w-20 text-right text-[12px] text-body">${(cost as number).toFixed(4)}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
