export class ApiError extends Error { constructor(public status: number, message: string) { super(message); this.name = 'ApiError'; } }

/** Typed client for the RAGeval API. */

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

const BASE = import.meta.env.VITE_API_BASE_URL || "";
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// One anonymous, per-browser id — keeps a visitor's own logged queries/scores from
// showing up on another visitor's dashboard. Not an auth credential.
function demoSessionId(): string {
  const key = "demo_session_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem(key, id);
  }
  return id;
}

async function req<T>(path: string, init?: RequestInit, retryCount = 0): Promise<T> {
  // Only retry GET (idempotent) requests.
  // Retrying POST mutations (e.g. /eval/log) after a network blip where the server
  // already committed the write causes duplicate rows, inflated metrics, and
  // duplicate alerts. For POSTs we fail immediately.
  const isGet = !init?.method || init.method.toUpperCase() === "GET";

  try {
    const headers = new Headers(init?.headers);
    headers.set("X-Demo-Session-Id", demoSessionId());
    const res = await fetch(BASE + path, { ...init, headers });
    if (!res.ok) {
      // Retry 5xx on GET requests only.
      if (isGet && res.status >= 500 && retryCount < 5) {
        await delay(2000 * (retryCount + 1));
        return req<T>(path, init, retryCount + 1);
      }
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail ?? JSON.stringify(body);
      } catch { /* keep statusText */ }
      throw new Error(`${res.status}: ${detail}`);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    // Only retry GET requests on network-level failures.
    if (isGet && retryCount < 5) {
      await delay(2000 * (retryCount + 1));
      return req<T>(path, init, retryCount + 1);
    }
    throw e;
  }
}

const post = (body: unknown) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export type RankingMetrics = { precision_at_k: number; recall_at_k: number; reciprocal_rank: number };
export type RetrievalStrategyResult = {
  mean_relevance: number;
  per_query_relevance: number[];
  precision_at_k?: number;
  recall_at_k?: number;
  mrr?: number;
  per_query_ranking?: RankingMetrics[];
};
export type RetrievalBenchResult = {
  strategy_a: RetrievalStrategyResult;
  strategy_b: RetrievalStrategyResult;
  winner: "a" | "b";
  has_ground_truth: boolean;
  precision_k: number;
  recall_k: number;
};

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
  retrievalBench: (
    queries: string[],
    a: string[][],
    b: string[][],
    relevantChunks?: string[][],
    precisionK = 5,
    recallK = 10,
  ) =>
    req<RetrievalBenchResult>(
      "/eval/retrieval-bench",
      post({
        queries,
        chunks_a: a,
        chunks_b: b,
        ...(relevantChunks ? { relevant_chunks: relevantChunks, precision_k: precisionK, recall_k: recallK } : {}),
      }),
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
