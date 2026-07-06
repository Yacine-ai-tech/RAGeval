/** Typed client for the RAGeval API (shapes verified in GAP_REPORT.md §1). */

export type Judge = { model: string; score: number };
export type Consensus = {
  consensus: number;
  stdev: number;
  judges: Judge[];
  judges_used: number;
  flag_for_review: boolean;
};

export type Scores = {
  relevance: number;
  groundedness: number;
  groundedness_consensus: Consensus;
  faithfulness: number;
  cost_usd: number;
  latency_ms: number;
  tokens_used: number;
  model: string;
  persona: string | null;
  persona_scope_violations: unknown[];
  overall_quality: number;
  flags: string[];
  needs_review: boolean;
};

export type Metrics = {
  total_queries: number;
  avg_relevance: number;
  avg_groundedness: number;
  avg_faithfulness: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  flagged_count: number;
};

export type QueryRow = {
  id: number;
  timestamp: string;
  query: string;
  answer: string | null;
  persona: string | null;
  model: string | null;
  relevance: number | null;
  groundedness: number | null;
  faithfulness: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  tokens_used: number | null;
  flags: string | null; // JSON-encoded string[]
  session_id: string | null;
  needs_review: number;
};

export type CostReport = {
  daily_costs: Record<string, number> | { day: string; cost: number }[];
  by_model: Record<string, number>;
  total_cost_usd: number;
  days: number;
};

export type ScorePayload = {
  query: string;
  answer: string;
  chunks: string[];
  tokens_used?: number;
  latency_ms?: number;
  model?: string;
  persona?: string | null;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch { /* keep statusText */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

const post = (body: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export type EvalEvent = { ts: string; kind: string; [k: string]: unknown };
export type EvalConfig = {
  judge_models: string[];
  embedding_model: string | null;
  disagreement_stdev_threshold: number;
  review_flags: string[];
};

export const api = {
  health: () => req<{ status: string }>("/health"),
  events: (limit = 100) => req<{ events: EvalEvent[]; capacity: number }>(`/eval/events?limit=${limit}`),
  config: () => req<EvalConfig>("/eval/config"),
  metrics: (days = 7) => req<Metrics>(`/eval/metrics?days=${days}`),
  queries: (limit = 50, needsReview?: boolean) =>
    req<QueryRow[]>(
      `/eval/queries?limit=${limit}${needsReview === undefined ? "" : `&needs_review=${needsReview}`}`,
    ),
  costReport: (days = 30) => req<CostReport>(`/eval/cost-report?days=${days}`),
  alerts: () => req<{ flagged_count: number; alerts: QueryRow[] }>("/eval/alerts"),
  score: (p: ScorePayload) => req<Scores>("/eval/score", post(p)),
  log: (p: ScorePayload & { session_id?: string }) => req<Scores>("/eval/log", post(p)),
  retrievalBench: (queries: string[], a: string[][], b: string[][]) =>
    req<{ strategy_a_mean: number; strategy_b_mean: number; winner: "a" | "b"; per_query_a: number[]; per_query_b: number[] }>(
      "/eval/retrieval-bench",
      post({ queries, chunks_a: a, chunks_b: b }),
    ),
  embeddingComparison: (queries: string[], chunks: string[][], models?: string[]) =>
    req<{ results: Record<string, number>; best: string | null }>(
      "/eval/embedding-comparison",
      post({ queries, chunks, ...(models ? { embedding_models: models } : {}) }),
    ),
};

export function parseFlags(row: QueryRow): string[] {
  try {
    const f = JSON.parse(row.flags ?? "[]");
    return Array.isArray(f) ? f : [];
  } catch {
    return [];
  }
}

export function scoreTone(v: number | null | undefined): "ok" | "warn" | "bad" | "default" {
  if (v == null) return "default";
  return v >= 0.75 ? "ok" : v >= 0.5 ? "warn" : "bad";
}

/* ---------- saved & pinned evaluations (local, v1 "saved evaluations" ask) ---------- */
export type SavedEval = { ts: number; label: string; payload: ScorePayload; scores: Scores };
const SAVED = "rageval.saved";
export function saveEval(e: SavedEval) {
  const list: SavedEval[] = JSON.parse(localStorage.getItem(SAVED) ?? "[]");
  list.unshift(e);
  localStorage.setItem(SAVED, JSON.stringify(list.slice(0, 40)));
}
export function readSaved(): SavedEval[] { try { return JSON.parse(localStorage.getItem(SAVED) ?? "[]"); } catch { return []; } }
export function deleteSaved(ts: number) {
  localStorage.setItem(SAVED, JSON.stringify(readSaved().filter((e) => e.ts !== ts)));
}
