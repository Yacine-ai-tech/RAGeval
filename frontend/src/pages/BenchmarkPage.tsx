import React from 'react';
import { PageHeader } from '../kit/AppShell';
import { Card } from '../kit/primitives';

// Benchmark results are rendered as actual React components (tables, headings,
// code blocks) instead of a raw <pre> dump of a Markdown string.

interface TableRow {
  metric: string;
  consensus: string;
  claude: string;
  groq: string;
}

const RESULTS: TableRow[] = [
  { metric: 'Accuracy',                    consensus: '0.800',   claude: '0.740', groq: '0.860 ★' },
  { metric: 'Precision',                   consensus: '0.812',   claude: '0.740', groq: '0.833'   },
  { metric: 'Recall',                      consensus: '0.780',   claude: '0.740', groq: '0.900 ★' },
  { metric: 'F1',                          consensus: '0.796',   claude: '0.740', groq: '0.865 ★' },
  { metric: 'ROC-AUC (raw consensus score)', consensus: '0.896 ★', claude: '—',  groq: '—'       },
];

export default function BenchmarkPage() {
  return (
    <div>
      <PageHeader
        title="Evaluation Benchmark"
        sub="Research-grade validation of the multi-judge groundedness consensus on HaluEval (Li et al., 2023), a standard hallucination benchmark."
      />

      <div className="space-y-5">
        {/* Setup */}
        <Card title="Setup">
          <ul className="space-y-1.5 text-sm text-dim">
            <li>
              <span className="font-medium text-body">Dataset:</span>{' '}
              HaluEval-QA. Each question yields <span className="num font-semibold">2</span> labelled examples against the same{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">knowledge</code> context: the{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">right_answer</code> (grounded=1) and{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">hallucinated_answer</code> (grounded=0).
            </li>
            <li>
              <span className="font-medium text-body">Judges configured:</span> the project's current default four-judge{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">JUDGE_MODELS</code> — Claude Haiku 4.5, Groq{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">gpt-oss-120b</code>, Gemini Flash, GPT-4o-mini.{' '}
              <span className="font-medium text-body">What actually responded:</span> Claude Haiku 4.5 and Groq{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">gpt-oss-120b</code> answered all 100 examples.
              Gemini's free-tier daily quota (20 requests/day) was already exhausted before this run started; GPT-4o-mini
              has no API key configured in this environment. RAGeval never substitutes a different judge or fails the whole
              call when one is unavailable — it scores from however many of the configured judges (minimum 2) actually
              respond. This run's consensus is a Claude+Groq average throughout.
            </li>
            <li>
              <span className="font-medium text-body">Decision threshold:</span> consensus ≥ 0.6 → &ldquo;grounded&rdquo;.
            </li>
            <li>
              <span className="font-medium text-body">N:</span>{' '}
              <span className="num">50</span> questions → <span className="num font-semibold">100</span> labelled examples (balanced).
            </li>
            <li>
              <span className="font-medium text-body">Reproduce:</span>{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">
                python eval/run_judge_benchmark.py --n 50
              </code>{' '}
              (needs <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">ANTHROPIC_API_KEY</code> /{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">GROQ_API_KEY</code>,{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">datasets</code>,{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">scikit-learn</code>).
            </li>
          </ul>
        </Card>

        {/* Results table */}
        <Card title="Results (real run)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[11px] font-medium uppercase tracking-wide text-muted">
                  <th className="pb-2 pr-6">Metric</th>
                  <th className="pb-2 pr-6 text-right">Consensus</th>
                  <th className="pb-2 pr-6 text-right">Claude Haiku (solo)</th>
                  <th className="pb-2 text-right">Groq gpt-oss-120b (solo)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {RESULTS.map((row) => (
                  <tr key={row.metric}>
                    <td className="py-2.5 pr-6 text-dim">{row.metric}</td>
                    <td className="num py-2.5 pr-6 text-right font-semibold text-body">{row.consensus}</td>
                    <td className="num py-2.5 pr-6 text-right text-muted">{row.claude}</td>
                    <td className="num py-2.5 text-right text-muted">{row.groq}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 rounded-xl border border-line bg-surface-2 p-4 text-[13px] leading-6 text-dim">
            <p>
              <span className="font-semibold text-body">Headline:</span> at N=100, Groq <code className="rounded bg-surface px-1 py-0.5 text-xs">gpt-oss-120b</code> solo
              (0.860 accuracy / 0.865 F1) outperformed the multi-judge consensus (0.800 / 0.796), which in turn beat Claude
              Haiku 4.5 solo (0.740 across the board). Consensus is an unweighted mean across whichever judges respond, and
              Claude was the meaningfully weaker judge here — averaging it in pulls the consensus below Groq's solo score.
              ROC-AUC 0.896 still shows the raw consensus score separates grounded from hallucinated answers well; it's
              specifically the threshold accuracy/F1 that a single strong judge beats at this sample size.
            </p>
            <p className="mt-2">
              <span className="font-semibold text-body">Honest caveat:</span> judge-disagreement (stdev) as an error predictor
              was a real signal here — 0.332 mean stdev on wrong predictions vs 0.074 on correct ones — but this remains a
              2-judge result (Gemini and GPT-4o-mini contributed nothing this run), not a true test of the full 4-judge
              panel, and unweighted averaging losing to the best single judge is itself evidence the aggregation method,
              not just the judge count, needs work before <code className="rounded bg-surface px-1 py-0.5 text-xs">flag_for_review</code> can
              be called a reliable hallucination alarm.
            </p>
          </div>
        </Card>

        {/* Scaling */}
        <Card title="Scaling">
          <p className="text-sm text-dim leading-6">
            N=50 keeps the run cheap (~200 judge calls, well under $1 — Claude Haiku and Groq gpt-oss-120b are both
            inexpensive per-token). Raising <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">--n</code> to a few
            hundred gives tighter confidence intervals; getting GPT-4o-mini and a non-quota-exhausted Gemini into the same
            run would test the full configured 4-judge panel instead of the 2 judges that actually responded here.
          </p>
        </Card>
      </div>
    </div>
  );
}
