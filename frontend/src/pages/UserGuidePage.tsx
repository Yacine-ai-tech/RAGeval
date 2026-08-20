import React from 'react';
import {
  BookOpen, Layers, Users, GitCompare, Radio, Sparkles, DollarSign,
  Terminal, Package, Scale, CheckCircle, Database, Gauge,
} from 'lucide-react';

function Code({ children }: { children: string }) {
  return (
    <pre className="bg-gray-950 text-green-300 text-xs md:text-sm font-mono p-4 rounded-lg overflow-x-auto border border-gray-800 whitespace-pre-wrap break-words">
      {children}
    </pre>
  );
}

function Section({
  icon: Icon,
  iconColor,
  title,
  children,
}: {
  icon: React.ElementType;
  iconColor: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-gray-800/50 backdrop-blur-md p-8 rounded-xl border border-gray-700 shadow-2xl">
      <h2 className="text-2xl font-bold mb-4 flex items-center gap-2 text-white">
        <Icon className={`w-6 h-6 ${iconColor}`} /> {title}
      </h2>
      <div className="space-y-4 text-sm text-gray-300 leading-relaxed">{children}</div>
    </section>
  );
}

export default function UserGuidePage() {
  return (
    <div className="p-8 max-w-5xl mx-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-8">
        <BookOpen className="w-10 h-10 text-blue-500" />
        <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
          RAGeval — User Guide
        </h1>
      </div>

      <p className="text-lg text-gray-300 mb-8 leading-relaxed">
        RAGeval is drop-in, self-hosted LLMOps observability for Retrieval-Augmented Generation systems.
        Wrap any RAG function with the <code className="text-green-300">@track</code> decorator (or call
        the REST API directly) and every interaction gets scored across 4 dimensions — relevance,
        groundedness, faithfulness, and persona-scope compliance — with multi-judge LLM consensus,
        cost/latency tracking, and automatic review flags, persisted to a SQLite (or Postgres) store
        with zero infrastructure to stand up first.
      </p>

      <div className="space-y-8">

        {/* What it actually does */}
        <Section icon={Layers} iconColor="text-blue-400" title="The 4 Score Dimensions">
          <p>Every scored interaction — from <code className="text-green-300">@track</code>, <code className="text-green-300">/eval/score</code>, or <code className="text-green-300">/eval/log</code> — returns:</p>
          <ul className="list-disc list-inside space-y-2 ml-2">
            <li><strong className="text-blue-300">Relevance</strong> — mean cosine similarity between the query and the retrieved chunks. Measures whether retrieval actually surfaced the right context.</li>
            <li><strong className="text-blue-300">Groundedness (multi-judge consensus)</strong> — how well the answer is supported by the retrieved context, per an LLM-judge panel (see below). This is the hallucination check.</li>
            <li><strong className="text-blue-300">Faithfulness</strong> — a per-sentence, embedding-similarity check: does every sentence in the answer trace back to something in a retrieved chunk, or did the model add unsupported detail?</li>
            <li><strong className="text-blue-300">Persona-scope compliance</strong> — for persona/RBAC-scoped assistants (e.g. a CFO bot vs a CHRO bot), flags when an answer surfaces figures from a business domain that persona shouldn't have access to.</li>
          </ul>
          <p>These roll up into a single <code className="text-green-300">overall_quality</code> score (a 0.4 / 0.4 / 0.2 weighting of relevance / groundedness / faithfulness) and a <code className="text-green-300">needs_review</code> flag whenever any check trips.</p>
        </Section>

        {/* Multi-judge consensus */}
        <Section icon={Users} iconColor="text-purple-400" title="Multi-Judge Consensus & Disagreement Flagging">
          <p>
            Groundedness isn't scored by a single model. By default RAGeval asks a panel of judges —
            Claude Haiku 4.5, Groq (openai/gpt-oss-120b), Gemini Flash, and GPT-4o-mini (configurable via
            the <code className="text-green-300">JUDGE_MODELS</code> env var, comma-separated) — the same
            question: "is this answer fully supported by the context?" Each judge returns a 0–1 score;
            judges whose provider key isn't configured are skipped, so the consensus only reflects
            models that actually voted. There's no single-judge fallback and no swapping one judge for
            another: consensus requires at least 2 judges to actually respond, both in how many are
            configured and how many are reachable at score time. Fall short of that and{' '}
            <code className="text-green-300">/eval/score</code> and{' '}
            <code className="text-green-300">/eval/log</code> return an honest 503 instead of a quietly
            degraded single-judge (or zero-judge) score.
          </p>
          <p>
            The mean across judges becomes the <code className="text-green-300">groundedness</code> score.
            RAGeval also computes the standard deviation across judge scores — when at least two judges
            answered and they disagree by more than 0.2 stdev, the interaction gets a{' '}
            <code className="text-green-300">JUDGE_DISAGREEMENT</code> flag. That disagreement is itself
            a useful signal: it tends to correlate with genuinely ambiguous or borderline answers that a
            single-judge system would silently pass or fail.
          </p>
          <p>Inspect the live judge configuration (models, embedding model, thresholds, flag codes) at any time via <code className="text-green-300">GET /eval/config</code>.</p>
        </Section>

        {/* Drop-in SDK */}
        <Section icon={Terminal} iconColor="text-orange-400" title="Drop-In Integration: the @track decorator">
          <p>The fastest way to instrument a RAG function — sync or async — is the decorator. It wraps your function, times it, scores the result, and persists it to the history store automatically:</p>
          <Code>{`from rageval import track

@track(model="anthropic/claude-sonnet-4-6", persona="cfo")
async def answer_question(query: str, context_chunks: list[str]) -> str:
    ...
    return answer`}</Code>
          <p>
            <code className="text-green-300">track()</code> takes two optional keyword args:{' '}
            <code className="text-green-300">model</code> (defaults to{' '}
            <code className="text-green-300">"groq/openai/gpt-oss-120b"</code>, used for cost
            calculation) and <code className="text-green-300">persona</code> (used for scope-compliance
            checks). Your wrapped function should accept <code className="text-green-300">query</code> as
            its first argument and return either the answer string directly, or a dict with{' '}
            <code className="text-green-300">answer</code> and optionally{' '}
            <code className="text-green-300">chunks</code> keys.
          </p>
          <p>No SDK access? The same pipeline is exposed over REST — see <code className="text-green-300">/eval/score</code> (score only) and <code className="text-green-300">/eval/log</code> (score + persist) on the API Docs page.</p>
        </Section>

        {/* Retrieval benchmarking */}
        <Section icon={GitCompare} iconColor="text-cyan-400" title="Retrieval-Strategy & Embedding Benchmarking">
          <p>
            Before committing to a retrieval approach, RAGeval can A/B it. <code className="text-green-300">POST /eval/retrieval-bench</code> takes
            the same set of queries retrieved through two different strategies (e.g. keyword vs
            hybrid search, or two chunk sizes) and always returns the mean embedding-relevance score
            for each — no labels required. Pass an optional <code className="text-green-300">relevant_chunks</code> array
            (the ground-truth relevant chunk text per query) to additionally get <code className="text-green-300">precision@k</code>,{' '}
            <code className="text-green-300">recall@k</code>, and <code className="text-green-300">MRR</code> — standard
            information-retrieval ranking metrics — for each strategy; when ground truth is supplied,
            the winner is decided by ranking quality rather than embedding similarity.
          </p>
          <p>
            <code className="text-green-300">POST /eval/embedding-comparison</code> does the analogous
            comparison across embedding models — score the same queries/chunks with each candidate model
            (default: <code className="text-green-300">BAAI/bge-m3</code> vs{' '}
            <code className="text-green-300">sentence-transformers/all-MiniLM-L6-v2</code>) and see which
            one retrieves more relevant context, before switching your production embedder.
          </p>
        </Section>

        {/* Cost tracking */}
        <Section icon={DollarSign} iconColor="text-amber-400" title="Cost & Token Tracking">
          <p>
            Every scored interaction reports <code className="text-green-300">cost_usd</code>, estimated
            from <code className="text-green-300">tokens_used</code> and the declared{' '}
            <code className="text-green-300">model</code> against a built-in per-1M-token pricing table
            covering Groq, Anthropic, and OpenAI models (unknown models simply cost $0 — extend the
            table for your own). <code className="text-green-300">GET /eval/cost-report</code> rolls this
            up by day and by model over a configurable window, and{' '}
            <code className="text-green-300">GET /eval/metrics</code> gives you the running total plus
            average latency for the same window.
          </p>
        </Section>

        {/* OTel */}
        <Section icon={Radio} iconColor="text-sky-400" title="OpenTelemetry Export (Optional)">
          <p>
            For teams that already run an OpenTelemetry collector (Jaeger, Grafana Tempo, or any
            OTLP-compatible backend), set <code className="text-green-300">RAGEVAL_OTEL_ENDPOINT</code> and
            RAGeval will export scored interactions as OTel spans via{' '}
            <code className="text-green-300">OTLPSpanExporter</code>, so RAGeval traces show up alongside
            the rest of your service traces instead of living only in its own dashboard. This is an
            optional dependency (<code className="text-green-300">opentelemetry-sdk</code> +{' '}
            <code className="text-green-300">opentelemetry-exporter-otlp</code>) — RAGeval works fully
            without it; the exporter no-ops when the package or endpoint isn't configured.
          </p>
        </Section>

        {/* DSPy */}
        <Section icon={Sparkles} iconColor="text-pink-400" title="DSPy Compilation Telemetry">
          <p>
            If your RAG pipeline uses DSPy prompt/program compilation, RAGeval's{' '}
            <code className="text-green-300">log_dspy_run()</code> helper (or the{' '}
            <code className="text-green-300">@dspy_compile_callback</code> decorator, which wraps your
            compile function and calls it for you) persists each compilation run — program name,
            candidate count, the winning candidate, and the optimization metric/score — into the same
            history store as live traffic. That means prompt-optimization experiments show up next to
            production interactions instead of in a separate silo, so you can see whether a DSPy
            recompile actually moved the quality metrics you care about. Both are in-process — no
            evaluator URL to configure, nothing to run — so a research script can log a compile run with
            zero network calls.
          </p>
        </Section>

        {/* Storage */}
        <Section icon={Database} iconColor="text-emerald-400" title="Storage: SQLite by Default, Postgres When You Need It">
          <p>
            No database to provision to get started: RAGeval writes to a local SQLite file (
            <code className="text-green-300">~/.rageval/rageval.db</code> by default, or wherever{' '}
            <code className="text-green-300">RAGEVAL_DB_PATH</code> points). Set{' '}
            <code className="text-green-300">RAGEVAL_POSTGRES_URL</code> (RAGeval's own dedicated var —
            not the generic <code className="text-green-300">POSTGRES_URL</code>, which would collide
            with a host app's own database if you're using <code className="text-green-300">@track</code>
            {' '}from inside another project) and it switches to Postgres with the same schema, plus
            pgvector storage for each interaction's query embedding — no code changes needed on your side.
          </p>
          <p>
            The hosted dashboard scopes reads to the current browser session via an{' '}
            <code className="text-green-300">X-Demo-Session-Id</code> header so visitors only see their
            own demo data; rows logged with no session id (e.g. your own backend dogfooding its RAG
            quality) stay visible platform-wide. This is a demo-isolation convenience, not a substitute
            for real auth in a production deployment.
          </p>
        </Section>

        {/* Positioning */}
        <Section icon={Gauge} iconColor="text-red-400" title="Where RAGeval Fits">
          <p>
            RAGeval is a small, self-hosted, single-purpose tool — not a bid to replace the larger
            observability platforms in this space (Phoenix, Langfuse, TruLens, and similar). Where it
            tries to differentiate honestly:
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>SQLite-default — a working setup in about 60 seconds, no database to stand up first.</li>
            <li>A genuinely drop-in decorator (<code className="text-green-300">@track</code>) rather than a client you wire through every call.</li>
            <li>Persona-scope awareness — not something the general-purpose LLM-observability tools model.</li>
            <li>Multi-judge consensus with explicit disagreement flagging, instead of a single-judge score.</li>
          </ul>
          <p>
            It does not ship enterprise features like SSO, Active Directory integration, or strict RBAC
            in the open-source tier — those are part of the optional commercial license for closed-source
            deployments (see below).
          </p>
        </Section>

        {/* PyPI / self-hosting */}
        <Section icon={Package} iconColor="text-indigo-400" title="Installation & Self-Hosting">
          <Code>{`pip install omnismart-rageval   # version 0.1.27 — import name stays \`rageval\`

rageval init                    # creates ~/.rageval/rageval.db
rageval serve --port 8003       # requires the [server] extra (uvicorn)`}</Code>
          <p>
            The core install is intentionally light — logging, the store, and{' '}
            <code className="text-green-300">@track</code> work with just the stdlib +{' '}
            <code className="text-green-300">python-dotenv</code>. Multi-judge scoring and embeddings
            need the heavier <code className="text-green-300">[eval]</code> extra (litellm, anthropic,
            groq, openai, google-genai, sentence-transformers, scikit-learn):
          </p>
          <Code>{`pip install "omnismart-rageval[eval]"     # + multi-judge scoring & embeddings
pip install "omnismart-rageval[server]"   # + run the bundled API (\`rageval serve\`)
pip install "omnismart-rageval[all]"      # everything`}</Code>
          <p>Prefer to run it as a hosted service instead? The live dashboard and API are reachable at the base URL shown on the API Docs page — no install required to try it.</p>
        </Section>

        {/* License */}
        <Section icon={Scale} iconColor="text-gray-300" title="License & Telemetry">
          <ul className="space-y-2">
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span>RAGeval is open-source under AGPL-3.0 — free for research, students, and OSS use. Deploying a modified version as a network service requires open-sourcing that backend too; a commercial license is available for closed-source or enterprise deployments.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span>The server sends an anonymous startup ping (timestamp + anonymized instance id, no prompts or keys) to help gauge usage. Set <code className="text-green-300">TELEMETRY_OPT_OUT=true</code> to disable it.</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
              <span>Never commit real API keys or <code className="text-green-300">.env</code> files — load credentials via environment variables, as shown in <code className="text-green-300">.env.example</code>.</span>
            </li>
          </ul>
        </Section>

      </div>
    </div>
  );
}
