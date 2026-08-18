import { useState } from "react";
import { Terminal, Copy, Check, Code2, Globe, Shield, Zap, BookOpen } from "lucide-react";

// Same resolution order as lib/api.ts's request client: an explicit VITE_API_BASE_URL
// (for split frontend/backend deployments) wins, otherwise fall back to the current
// origin (same-origin deployments, e.g. the Docker single-container setup) — so the
// copy-paste examples always match wherever this page is actually being served from,
// author's deployment or any self-hoster's, instead of a hardcoded URL.
const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" ? window.location.origin : "");

type Endpoint = {
  group: string;
  method: "GET" | "POST";
  path: string;
  desc: string;
  body: string | null;
  response: string;
};

// The full, real API surface — 12 endpoints, verified directly against api.py.
const ENDPOINTS: Endpoint[] = [
  // ── System ──────────────────────────────────────────────────────────────
  {
    group: "System",
    method: "GET",
    path: "/",
    desc: "Serves the built dashboard SPA (frontend/dist/index.html) when it's bundled alongside the API. Falls back to a plain JSON pointer to /docs when no built frontend is present (e.g. a bare `pip install` deployment).",
    body: null,
    response: `{"service": "rageval", "docs": "/docs"}`,
  },
  {
    group: "System",
    method: "GET",
    path: "/health",
    desc: "Liveness check. Not gated by the internal-token middleware — always reachable, used for uptime probes and the frontend's \"waking backend\" retry loop.",
    body: null,
    response: `{"status": "ok", "service": "rageval", "version": "0.1.23"}`,
  },
  // ── Scoring ─────────────────────────────────────────────────────────────
  {
    group: "Scoring",
    method: "POST",
    path: "/eval/score",
    desc: "Score a query/answer/chunks triple across all 4 dimensions — relevance, groundedness (multi-judge consensus), faithfulness, and persona-scope compliance. Does NOT write to the history store; use this for stateless, on-the-fly scoring (e.g. a CI gate or a playground UI). Requires >=2 configured judges to actually respond — with fewer, this returns 503 rather than a silently-degraded single-judge score (see Errors below).",
    body: `{
  "query": "What was Q2 gross margin?",
  "answer": "Q2 gross margin was 41.2%, up 3 points from Q1.",
  "chunks": [
    "Q2 gross margin came in at 41.2%, driven by lower COGS...",
    "Q1 gross margin was 38.4%..."
  ],
  "tokens_used": 180,
  "latency_ms": 1240,
  "model": "groq/openai/gpt-oss-120b",
  "persona": "cfo"
}`,
    response: `{
  "relevance": 0.87,
  "groundedness": 0.83,
  "groundedness_consensus": {
    "consensus": 0.83,
    "stdev": 0.05,
    "judges": [
      {"model": "anthropic/claude-haiku-4-5", "score": 0.85},
      {"model": "groq/openai/gpt-oss-120b", "score": 0.8},
      {"model": "gemini/gemini-flash-latest", "score": 0.84}
    ],
    "judges_used": 3,
    "flag_for_review": false
  },
  "faithfulness": 0.91,
  "cost_usd": 0.00031,
  "latency_ms": 1240.0,
  "tokens_used": 180,
  "model": "groq/openai/gpt-oss-120b",
  "persona": "cfo",
  "persona_scope_violations": [],
  "overall_quality": 0.856,
  "flags": [],
  "needs_review": false,
  "query_embedding": null
}

// 503 (fewer than 2 judges configured/reachable):
// {"detail": "Only 1 of 3 configured judges responded (need at least 2). ..."}`,
  },
  {
    group: "Scoring",
    method: "POST",
    path: "/eval/log",
    desc: "Same scoring pipeline as /eval/score (same >=2 judge requirement, same 503 on failure), PLUS persists the interaction + scores to the history store (SQLite by default, Postgres if RAGEVAL_POSTGRES_URL is set). This is what the @track decorator and the drop-in SDK call under the hood. Optionally accepts session_id in the body — used by service-to-service callers (no browser) that want their rows kept platform-visible; browser callers should send X-Demo-Session-Id instead (see note above).",
    body: `{
  "query": "What was Q2 gross margin?",
  "answer": "Q2 gross margin was 41.2%, up 3 points from Q1.",
  "chunks": ["Q2 gross margin came in at 41.2%..."],
  "tokens_used": 180,
  "latency_ms": 1240,
  "model": "groq/openai/gpt-oss-120b",
  "persona": "cfo",
  "session_id": "my-app-001"
}`,
    response: `{
  "relevance": 0.87,
  "groundedness": 0.83,
  "groundedness_consensus": { "consensus": 0.83, "stdev": 0.05, "judges": [...], "judges_used": 3, "flag_for_review": false },
  "faithfulness": 0.91,
  "cost_usd": 0.00031,
  "latency_ms": 1240.0,
  "tokens_used": 180,
  "model": "groq/openai/gpt-oss-120b",
  "persona": "cfo",
  "persona_scope_violations": [],
  "overall_quality": 0.856,
  "flags": [],
  "needs_review": false,
  "query_embedding": null  // a real [float, ...] vector instead of null when RAGEVAL_POSTGRES_URL (pgvector) is configured
}`,
  },
  // ── Observability ───────────────────────────────────────────────────────
  {
    group: "Observability",
    method: "GET",
    path: "/eval/metrics?days=7",
    desc: "Aggregate metrics over the last N days (default 7): averages for relevance/groundedness/faithfulness/latency, total cost, and the count of flagged (needs_review) interactions.",
    body: null,
    response: `{
  "total_queries": 142,
  "avg_relevance": 0.88,
  "avg_groundedness": 0.84,
  "avg_faithfulness": 0.91,
  "avg_latency_ms": 980.4,
  "total_cost_usd": 0.041,
  "flagged_count": 9,
  "query_volume_by_hour": []
}`,
  },
  {
    group: "Observability",
    method: "GET",
    path: "/eval/queries?limit=50&needs_review=true",
    desc: "Raw query log, most recent first. limit caps the row count (default 50); needs_review filters to only flagged (true) or only clean (false) rows when passed, or returns both when omitted.",
    body: null,
    response: `[
  {
    "id": 42,
    "timestamp": "2026-08-08T14:03:12.441000+00:00",
    "query": "What was Q2 gross margin?",
    "answer": "Q2 gross margin was 41.2%...",
    "persona": "cfo",
    "model": "groq/openai/gpt-oss-120b",
    "relevance": 0.87,
    "groundedness": 0.83,
    "faithfulness": 0.91,
    "cost_usd": 0.00031,
    "latency_ms": 1240.0,
    "tokens_used": 180,
    "flags": "[]",
    "session_id": "my-app-001",
    "needs_review": 0
  }
]`,
  },
  {
    group: "Observability",
    method: "GET",
    path: "/eval/cost-report?days=30",
    desc: "Cost breakdown over the last N days (default 30), grouped by day and by model, plus a running total.",
    body: null,
    response: `{
  "daily_costs": {"2026-08-07": 0.012, "2026-08-08": 0.029},
  "by_model": {"groq/openai/gpt-oss-120b": 0.031, "anthropic/claude-sonnet-4-6": 0.01},
  "total_cost_usd": 0.041,
  "days": 30
}`,
  },
  {
    group: "Observability",
    method: "GET",
    path: "/eval/alerts",
    desc: "The 10 most recent flagged (needs_review) interactions, plus a total flagged count. A quick way to see what's currently failing quality checks without paging through /eval/queries.",
    body: null,
    response: `{
  "flagged_count": 9,
  "alerts": [
    {
      "id": 40,
      "query": "What's our current headcount?",
      "persona": "cfo",
      "flags": "[\\"PERSONA_SCOPE_VIOLATION\\"]",
      "needs_review": 1
    }
  ]
}`,
  },
  {
    group: "Observability",
    method: "GET",
    path: "/eval/events?limit=100",
    desc: "Live telemetry ring buffer (in-memory, process-local, capacity 200): the most recent evaluation-pipeline events — one per /eval/score or /eval/log call, both when a request comes in (interaction.received) and when scoring finishes (interaction.scored). Powers the dashboard's Live Traces view.",
    body: null,
    response: `{
  "events": [
    {
      "ts": "2026-08-08T14:03:12.550Z",
      "kind": "interaction.scored",
      "route": "/eval/log",
      "overall": 0.856,
      "judges_used": 3,
      "flags": [],
      "persisted": true
    }
  ],
  "capacity": 200
}`,
  },
  {
    group: "Observability",
    method: "GET",
    path: "/eval/config",
    desc: "Factual evaluator configuration — no secrets. Which judge models are configured, the embedding model, the judge-disagreement stdev threshold, and the full set of review-flag codes the scorer can emit.",
    body: null,
    response: `{
  "judge_models": [
    "anthropic/claude-haiku-4-5",
    "groq/openai/gpt-oss-120b",
    "gemini/gemini-flash-latest",
    "openai/gpt-4o-mini"
  ],
  "embedding_model": "BAAI/bge-m3",
  "disagreement_stdev_threshold": 0.2,
  "review_flags": [
    "LOW_RETRIEVAL_RELEVANCE",
    "POTENTIAL_HALLUCINATION",
    "HIGH_LATENCY",
    "JUDGE_DISAGREEMENT",
    "PERSONA_SCOPE_VIOLATION"
  ]
}`,
  },
  // ── Benchmarking ────────────────────────────────────────────────────────
  {
    group: "Benchmarking",
    method: "POST",
    path: "/eval/retrieval-bench",
    desc: "A/B compare two retrieval strategies on the same set of queries. chunks_a and chunks_b must each have one ranked chunk-list per query (same length as queries, or a 400 length_mismatch is returned). Always returns each strategy's mean embedding-relevance score (no labels needed). Optionally pass relevant_chunks — the ground-truth relevant chunk text per query — to also get precision@k, recall@k, and MRR (standard IR ranking metrics); when supplied, the winner is decided by ranking quality (precision/recall F1) rather than embedding similarity.",
    body: `{
  "queries": ["What is our refund policy?"],
  "chunks_a": [["Refunds are processed within 5 business days...", "Store credit is issued..."]],
  "chunks_b": [["Our return policy allows 30 days...", "Refund requests go through support..."]],
  "relevant_chunks": [["Refunds are processed within 5 business days..."]],
  "precision_k": 5,
  "recall_k": 10
}`,
    response: `{
  "strategy_a": {
    "mean_relevance": 0.71,
    "per_query_relevance": [0.71],
    "precision_at_k": 0.2,
    "recall_at_k": 1.0,
    "mrr": 1.0,
    "per_query_ranking": [{"precision_at_k": 0.2, "recall_at_k": 1.0, "reciprocal_rank": 1.0}]
  },
  "strategy_b": {
    "mean_relevance": 0.84,
    "per_query_relevance": [0.84],
    "precision_at_k": 0.0,
    "recall_at_k": 0.0,
    "mrr": 0.0,
    "per_query_ranking": [{"precision_at_k": 0.0, "recall_at_k": 0.0, "reciprocal_rank": 0.0}]
  },
  "winner": "a",
  "has_ground_truth": true,
  "precision_k": 5,
  "recall_k": 10
}`,
  },
  {
    group: "Benchmarking",
    method: "POST",
    path: "/eval/embedding-comparison",
    desc: "Score the same queries/chunks with multiple embedding models and compare retrieval-relevance means side by side. embedding_models defaults to [\"BAAI/bge-m3\", \"sentence-transformers/all-MiniLM-L6-v2\"] when omitted. Useful for picking an embedding model before committing to it in production.",
    body: `{
  "queries": ["What is our refund policy?"],
  "chunks": [["Refunds are processed within 5 business days...", "Store credit is issued..."]],
  "embedding_models": ["BAAI/bge-m3", "sentence-transformers/all-MiniLM-L6-v2"]
}`,
    response: `{
  "results": {
    "BAAI/bge-m3": 0.81,
    "sentence-transformers/all-MiniLM-L6-v2": 0.76
  },
  "best": "BAAI/bge-m3"
}`,
  },
];

const SNIPPETS = {
  curl: (ep: Endpoint) =>
    ep.body
      ? `curl -X ${ep.method} "${BASE_URL}${ep.path}" \\\n  -H "Content-Type: application/json" \\\n  -H "X-Demo-Session-Id: my-app-001" \\\n  -d '${ep.body}'`
      : `curl "${BASE_URL}${ep.path}" \\\n  -H "X-Demo-Session-Id: my-app-001"`,
  python: (ep: Endpoint) =>
    ep.body
      ? `import requests\n\nresp = requests.${ep.method.toLowerCase()}(\n  "${BASE_URL}${ep.path}",\n  headers={"X-Demo-Session-Id": "my-app-001"},\n  json=...,  # see request body\n)\nprint(resp.json())`
      : `import requests\n\nresp = requests.get(\n  "${BASE_URL}${ep.path}",\n  headers={"X-Demo-Session-Id": "my-app-001"},\n)\nprint(resp.json())`,
  node: (ep: Endpoint) =>
    ep.body
      ? `const res = await fetch("${BASE_URL}${ep.path}", {\n  method: "${ep.method}",\n  headers: {\n    "Content-Type": "application/json",\n    "X-Demo-Session-Id": "my-app-001",\n  },\n  body: JSON.stringify(/* see request body */),\n});\nconst data = await res.json();`
      : `const res = await fetch("${BASE_URL}${ep.path}", {\n  headers: { "X-Demo-Session-Id": "my-app-001" },\n});\nconst data = await res.json();\nconsole.log(data);`,
};

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return <button onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }} style={{ background:"none",border:"none",cursor:"pointer",color:copied?"#4ade80":"#94a3b8",padding:"4px" }}>{copied ? <Check size={14} /> : <Copy size={14} />}</button>;
}

function CodeBlock({ code }: { code: string }) {
  return <div style={{ position:"relative",background:"rgba(0,0,0,0.4)",borderRadius:8,padding:"14px 40px 14px 14px",fontFamily:"monospace",fontSize:"0.78rem",color:"#e2e8f0",whiteSpace:"pre-wrap",wordBreak:"break-all",lineHeight:1.6 }}>
    <div style={{ position:"absolute",top:8,right:8 }}><CopyBtn text={code} /></div>
    {code}
  </div>;
}

export default function ApiDocs() {
  const [lang, setLang] = useState("curl");
  const [active, setActive] = useState(0);
  const ep = ENDPOINTS[active];
  return (
    <div style={{ padding:"24px 32px",maxWidth:1100,color:"#e2e8f0" }}>
      <div style={{ display:"flex",alignItems:"center",gap:12,marginBottom:8 }}>
        <Terminal size={28} color="#38bdf8" />
        <div>
          <h1 style={{ fontSize:"1.5rem",fontWeight:700,margin:0 }}>{"RAGeval API Reference"}</h1>
          <p style={{ margin:0,fontSize:"0.85rem",color:"#94a3b8" }}>{"Score and observe RAG pipelines programmatically — the full REST surface behind the @track decorator"}</p>
        </div>
      </div>
      <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))",gap:12,margin:"20px 0" }}>
        {[
          { icon: Globe, label:"Base URL", value:BASE_URL, color:"#38bdf8" },
          { icon: Shield, label:"Auth", value:"X-RAGeval-Internal-Token (opt-in)", color:"#4ade80" },
          { icon: Zap, label:"Format", value:"REST / JSON", color:"#f59e0b" },
          { icon: BookOpen, label:"Latency", value:"<2s avg", color:"#a78bfa" },
        ].map(({icon:Icon,label,value,color}) => (
          <div key={label} style={{ background:"rgba(255,255,255,0.04)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:10,padding:"12px 16px",display:"flex",gap:10,alignItems:"center" }}>
            <Icon size={18} color={color} />
            <div><div style={{ fontSize:"0.7rem",color:"#64748b",textTransform:"uppercase",letterSpacing:"0.05em" }}>{label}</div><div style={{ fontSize:"0.85rem",fontWeight:600 }}>{value}</div></div>
          </div>
        ))}
      </div>
      <div style={{ background:"rgba(56,189,248,0.06)",border:"1px solid rgba(56,189,248,0.2)",borderRadius:10,padding:"10px 14px",marginBottom:20,fontSize:"0.78rem",color:"#94a3b8",lineHeight:1.6 }}>
        <strong style={{ color:"#38bdf8" }}>Implementation note:</strong> the GET read endpoints below (<code>/eval/metrics</code>, <code>/eval/queries</code>, <code>/eval/cost-report</code>, <code>/eval/alerts</code>) scope their results to the caller via an optional <code>X-Demo-Session-Id</code> header — send the same id your app uses elsewhere and you'll only see your own rows; omit it and rows with no session (platform/service telemetry) are returned instead.
      </div>
      <div style={{ display:"grid",gridTemplateColumns:"260px 1fr",gap:20 }}>
        <div style={{ display:"flex",flexDirection:"column",gap:6 }}>
          {ENDPOINTS.map((e, i) => {
            const showGroup = i === 0 || ENDPOINTS[i - 1].group !== e.group;
            return (
              <div key={i}>
                {showGroup && (
                  <div style={{ fontSize:"0.7rem",color:"#64748b",textTransform:"uppercase",letterSpacing:"0.06em",margin:i===0?"0 0 4px":"14px 0 4px" }}>{e.group}</div>
                )}
                <button onClick={()=>setActive(i)} style={{ width:"100%",textAlign:"left",background:active===i?"rgba(124,58,237,0.15)":"rgba(255,255,255,0.03)",border:active===i?"1px solid rgba(124,58,237,0.4)":"1px solid rgba(255,255,255,0.07)",borderRadius:8,padding:"10px 14px",cursor:"pointer" }}>
                  <span style={{ fontSize:"0.68rem",fontWeight:700,fontFamily:"monospace",background:e.method==="GET"?"rgba(56,189,248,0.15)":"rgba(167,139,250,0.15)",color:e.method==="GET"?"#38bdf8":"#a78bfa",borderRadius:4,padding:"2px 6px",marginRight:8 }}>{e.method}</span>
                  <span style={{ fontSize:"0.8rem",fontFamily:"monospace",color:active===i?"#e2e8f0":"#94a3b8" }}>{e.path}</span>
                </button>
              </div>
            );
          })}
        </div>
        <div style={{ display:"flex",flexDirection:"column",gap:14 }}>
          <div style={{ background:"rgba(255,255,255,0.04)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:12,padding:"16px 20px" }}>
            <div style={{ display:"flex",alignItems:"center",gap:10,marginBottom:10 }}>
              <span style={{ fontSize:"0.75rem",fontWeight:700,fontFamily:"monospace",background:ep.method==="GET"?"rgba(56,189,248,0.15)":"rgba(167,139,250,0.15)",color:ep.method==="GET"?"#38bdf8":"#a78bfa",borderRadius:5,padding:"3px 8px" }}>{ep.method}</span>
              <code style={{ fontSize:"0.9rem" }}>{BASE_URL}{ep.path}</code>
            </div>
            <p style={{ margin:0,fontSize:"0.85rem",color:"#94a3b8" }}>{ep.desc}</p>
          </div>
          {ep.body && <div><div style={{ fontSize:"0.75rem",color:"#64748b",marginBottom:6,display:"flex",alignItems:"center",gap:6 }}><Code2 size={13} /> Request body</div><CodeBlock code={ep.body} /></div>}
          <div>
            <div style={{ display:"flex",gap:6,marginBottom:8,alignItems:"center" }}>
              <span style={{ fontSize:"0.75rem",color:"#64748b",marginRight:4 }}>Language:</span>
              {["curl","python","node"].map(l => <button key={l} onClick={()=>setLang(l)} style={{ padding:"4px 12px",borderRadius:6,border:"1px solid",borderColor:lang===l?"#7c3aed":"rgba(255,255,255,0.1)",background:lang===l?"rgba(124,58,237,0.2)":"transparent",color:lang===l?"#c4b5fd":"#94a3b8",cursor:"pointer",fontSize:"0.78rem",fontWeight:600 }}>{l}</button>)}
            </div>
            <CodeBlock code={(SNIPPETS as Record<string, (ep: Endpoint) => string>)[lang](ep)} />
          </div>
          <div><div style={{ fontSize:"0.75rem",color:"#64748b",marginBottom:6,display:"flex",alignItems:"center",gap:6 }}><Check size={13} color="#4ade80" /> Sample response</div><CodeBlock code={ep.response} /></div>
        </div>
      </div>
    </div>
  );
}
