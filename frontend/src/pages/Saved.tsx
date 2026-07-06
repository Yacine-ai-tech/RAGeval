import { useState } from "react";
import { Bookmark, Trash2, RotateCw, AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../kit/AppShell";
import { Button, Card, Chip, EmptyState } from "../kit/primitives";
import { JSONViewer } from "../kit/JSONViewer";
import { api, deleteSaved, readSaved, SavedEval, Scores, scoreTone } from "../lib/api";

/* v1 "saved evaluations" + re-score — pinned evaluations persisted locally, each
   re-runnable against the live scorer to compare drift over time. */

export default function Saved() {
  const [items, setItems] = useState<SavedEval[]>(readSaved());
  const [open, setOpen] = useState<number | null>(null);
  const [rescored, setRescored] = useState<Record<number, Scores | { error: string }>>({});
  const [busy, setBusy] = useState<number | null>(null);

  const rescore = async (e: SavedEval) => {
    setBusy(e.ts);
    try {
      const scores = await api.score(e.payload);
      setRescored((r) => ({ ...r, [e.ts]: scores }));
    } catch (err) {
      setRescored((r) => ({ ...r, [e.ts]: { error: err instanceof Error ? err.message : String(err) } }));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <PageHeader
        title="Saved evaluations"
        sub="Pinned evaluations kept in this browser. Re-score any of them against the live pipeline to watch quality drift."
        actions={items.length > 0 && (
          <Button variant="ghost" onClick={() => { localStorage.removeItem("rageval.saved"); setItems([]); }}>
            <Trash2 size={14} /> Clear all
          </Button>
        )}
      />
      {items.length === 0 ? (
        <Card>
          <EmptyState icon={Bookmark} title="Nothing saved yet"
            hint="On the Evaluate page, score an interaction and use “Save” to pin it here."
            action={<Link to="/evaluate" className="text-sm underline decoration-dotted text-dim hover:text-body">Open Evaluate</Link>} />
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((e, i) => {
            const rs = rescored[e.ts];
            const orig = e.scores.overall_quality;
            const now = rs && !("error" in rs) ? rs.overall_quality : null;
            const delta = now != null ? now - orig : null;
            return (
              <Card key={e.ts}>
                <button className="flex w-full flex-wrap items-center gap-3 text-left" onClick={() => setOpen(open === i ? null : i)}>
                  <Bookmark size={15} className="shrink-0 text-dim" />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-body">{e.label}</span>
                  {e.payload.persona && <Chip>{e.payload.persona}</Chip>}
                  <Chip tone={scoreTone(orig)} className="num">saved {orig.toFixed(2)}</Chip>
                  {now != null && <Chip tone={scoreTone(now)} className="num">now {now.toFixed(2)}</Chip>}
                  {delta != null && <Chip tone={Math.abs(delta) < 0.05 ? "default" : delta > 0 ? "ok" : "bad"} className="num">
                    {delta >= 0 ? "+" : ""}{delta.toFixed(2)}
                  </Chip>}
                  <span className="num text-[11.5px] text-muted">{new Date(e.ts).toLocaleDateString()}</span>
                </button>
                {open === i && (
                  <div className="mt-4 space-y-3 border-t border-line pt-4">
                    <Button variant="secondary" onClick={() => rescore(e)} disabled={busy === e.ts}>
                      <RotateCw size={13} className={busy === e.ts ? "animate-spin" : ""} /> {busy === e.ts ? "Re-scoring…" : "Re-score now"}
                    </Button>
                    {rs && "error" in rs && <div className="flex items-center gap-2 text-[13px] text-bad"><AlertTriangle size={14} />{rs.error}</div>}
                    <div className="grid gap-3 lg:grid-cols-2">
                      <div>
                        <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted">Interaction</div>
                        <JSONViewer data={e.payload} maxHeight={200} />
                      </div>
                      <div>
                        <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted">{rs && !("error" in rs) ? "Re-scored" : "Saved scores"}</div>
                        <JSONViewer data={rs && !("error" in rs) ? rs : e.scores} maxHeight={200} />
                      </div>
                    </div>
                    <button className="text-[12px] text-bad underline decoration-dotted" onClick={() => { deleteSaved(e.ts); setItems(readSaved()); }}>
                      Remove this evaluation
                    </button>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
