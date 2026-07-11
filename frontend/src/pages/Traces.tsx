import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Pause, Play, RadioTower } from "lucide-react";
import { PageHeader } from "../kit/AppShell";
import { Card, Chip, EmptyState } from "../kit/primitives";
import { JSONViewer } from "../kit/JSONViewer";
import { api, EvalEvent } from "../lib/api";

/* v1 "Live Traces" — real telemetry from the evaluation pipeline, polled from the
   in-memory event ring (/eval/events). Every score/receipt emits an event. */

const KIND_TONE: Record<string, "ok" | "warn" | "accent" | "default"> = {
  "interaction.received": "accent",
  "interaction.scored": "ok",
};

export default function Traces() {
  const [events, setEvents] = useState<EvalEvent[] | null>(null);
  const [paused, setPaused] = useState(false);
  const [sel, setSel] = useState<EvalEvent | null>(null);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useEffect(() => {
    let alive = true;
    const tick = () => api.events(150).then((r) => { if (alive && !pausedRef.current) setEvents(r.events); }).catch(() => {});
    tick();
    const t = setInterval(tick, 2000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  return (
    <div>
      <PageHeader
        title="Live traces"
        sub="Real-time telemetry emitted by the evaluation pipeline as interactions are received and scored."
        actions={
          <div className="flex items-center gap-2">
            <Chip tone={paused ? "warn" : "ok"}><RadioTower size={11} /> {paused ? "paused" : "live"}</Chip>
            <button className="flex items-center gap-1.5 rounded-btn border border-line-strong px-3 py-2 text-sm text-body hover:bg-surface-2" onClick={() => setPaused((p) => !p)}>
              {paused ? <Play size={13} /> : <Pause size={13} />} {paused ? "Resume" : "Pause"}
            </button>
          </div>
        }
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <Card title="Event stream" noPad className="overflow-hidden">
          {!events ? (
            <div className="p-5"><EmptyState icon={Activity} title="Connecting to telemetry…" /></div>
          ) : events.length === 0 ? (
            <EmptyState icon={Activity} title="No events yet"
              hint="Score an interaction on the Evaluate page — receipt and score events appear here instantly." />
          ) : (
            <div className="max-h-[560px] divide-y divide-[var(--border)] overflow-y-auto">
              <AnimatePresence initial={false}>
                {events.map((e, i) => (
                  <motion.button key={`${e.ts}-${i}`} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-2" onClick={() => setSel(e)}>
                    <Chip tone={KIND_TONE[e.kind] ?? "default"}>{e.kind}</Chip>
                    <span className="min-w-0 flex-1 truncate text-[13px] text-dim">
                      {typeof e.query === "string" ? e.query : e.route as string}
                      {Array.isArray(e.flags) && e.flags.length > 0 ? <span className="text-bad"> · {(e.flags as string[]).length} flag(s)</span> : null}
                      {typeof e.overall === "number" ? <span className="text-muted"> · overall {(e.overall as number).toFixed(2)}</span> : null}
                    </span>
                    <span className="num text-[11px] text-muted">{new Date(e.ts).toLocaleTimeString()}</span>
                  </motion.button>
                ))}
              </AnimatePresence>
            </div>
          )}
        </Card>
        <Card title="Event detail">
          {sel ? <JSONViewer data={sel} maxHeight={520} /> : <EmptyState title="Select an event" hint="Click any event to inspect its full payload." />}
        </Card>
      </div>
    </div>
  );
}
