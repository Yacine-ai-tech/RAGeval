import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, ListTree, RefreshCw } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState, Skeleton } from "../kit/primitives";
import { Segmented, Select } from "../kit/misc";
import { JSONViewer } from "../kit/JSONViewer";
import { api, parseFlags, QueryRow, scoreTone } from "../lib/api";

export default function Queries() {
  const [rows, setRows] = useState<QueryRow[] | null>(null);
  const [filter, setFilter] = useState("all");
  const [limit, setLimit] = useState("50");
  const [err, setErr] = useState("");

  const load = () => {
    setRows(null);
    setErr("");
    api
      .queries(Number(limit), filter === "all" ? undefined : true)
      .then(setRows)
      .catch((e) => setErr(String(e)));
  };
  useEffect(load, [filter, limit]);

  return (
    <div>
      <PageHeader
        title="Queries & traces"
        sub="Every tracked interaction with its real evaluation scores. Expand a row to inspect the full stored trace."
        actions={
          <div className="flex items-center gap-2">
            <Segmented
              value={filter}
              onChange={setFilter}
              options={[{ value: "all", label: "All" }, { value: "flagged", label: "Needs review" }]}
            />
            <Select value={limit} onChange={setLimit} options={["25", "50", "100", "200"].map((v) => ({ value: v, label: `last ${v}` }))} />
            <Button variant="ghost" onClick={load} aria-label="refresh"><RefreshCw size={14} /></Button>
          </div>
        }
      />

      {err && <Card><div className="text-sm text-bad">{err}</div></Card>}
      {!rows ? (
        <Skeleton className="h-72 w-full" />
      ) : rows.length === 0 ? (
        <Card>
          <EmptyState
            icon={ListTree}
            title={filter === "flagged" ? "Nothing flagged — judges agree and scores are healthy" : "No tracked queries yet"}
            hint="Interactions logged via @track or /eval/log appear here with their evaluation scores."
          />
        </Card>
      ) : (
        <Card noPad className="overflow-hidden">
          <div className="grid grid-cols-[1fr_repeat(3,72px)_90px] gap-2 border-b border-line px-5 py-2.5 text-[11px] font-medium uppercase tracking-wide text-muted max-md:grid-cols-[1fr_90px]">
            <span>Query</span>
            <span className="max-md:hidden">Relev.</span>
            <span className="max-md:hidden">Ground.</span>
            <span className="max-md:hidden">Faith.</span>
            <span>Flags</span>
          </div>
          <div className="divide-y divide-[var(--border)]">
            {rows.map((r) => <Row key={r.id} r={r} />)}
          </div>
        </Card>
      )}
    </div>
  );
}

function Score({ v }: { v: number | null }) {
  const tone = scoreTone(v);
  const color = tone === "ok" ? "var(--success)" : tone === "warn" ? "var(--warning)" : tone === "bad" ? "var(--danger)" : "var(--text-muted)";
  return <span className="num text-[13px]" style={{ color }}>{v == null ? "—" : v.toFixed(2)}</span>;
}

function Row({ r }: { r: QueryRow }) {
  const [open, setOpen] = useState(false);
  const flags = parseFlags(r);
  return (
    <div className={flags.length ? "bg-[rgba(255,107,107,0.04)]" : ""}>
      <button className="grid w-full grid-cols-[1fr_repeat(3,72px)_90px] items-center gap-2 px-5 py-3 text-left hover:bg-surface-2 max-md:grid-cols-[1fr_90px]" onClick={() => setOpen((o) => !o)}>
        <span className="flex min-w-0 items-center gap-2">
          {open ? <ChevronDown size={13} className="shrink-0 text-muted" /> : <ChevronRight size={13} className="shrink-0 text-muted" />}
          <span className="min-w-0">
            <span className="block truncate text-sm text-body">{r.query}</span>
            <span className="block text-[11px] text-muted">
              {new Date(r.timestamp).toLocaleString()} {r.persona ? `· persona: ${r.persona}` : ""} {r.model ? `· ${r.model}` : ""}
            </span>
          </span>
        </span>
        <span className="max-md:hidden"><Score v={r.relevance} /></span>
        <span className="max-md:hidden"><Score v={r.groundedness} /></span>
        <span className="max-md:hidden"><Score v={r.faithfulness} /></span>
        <span className="flex flex-wrap gap-1">
          {flags.length === 0 ? <Chip tone="ok">clean</Chip> : flags.slice(0, 1).map((f) => <Chip key={f} tone="bad" title={flags.join(", ")}>{f.replaceAll("_", " ").toLowerCase()}{flags.length > 1 ? ` +${flags.length - 1}` : ""}</Chip>)}
        </span>
      </button>
      {open && (
        <div className="space-y-3 px-5 pb-4">
          {r.answer && (
            <div className="rounded-xl border border-line bg-surface-2 p-3.5 text-[13px] leading-6 text-dim">
              {r.answer}
            </div>
          )}
          <div className="flex flex-wrap gap-1.5">
            {flags.map((f) => <Chip key={f} tone="bad">{f}</Chip>)}
            {r.latency_ms != null && <Chip className="num">{Math.round(r.latency_ms)} ms</Chip>}
            {r.cost_usd != null && <Chip className="num">${r.cost_usd.toFixed(5)}</Chip>}
            {r.tokens_used != null && <Chip className="num">{r.tokens_used} tok</Chip>}
            {r.session_id && <Chip title="session">{r.session_id.slice(0, 12)}</Chip>}
          </div>
          <JSONViewer data={{ ...r, flags }} maxHeight={260} />
        </div>
      )}
    </div>
  );
}
