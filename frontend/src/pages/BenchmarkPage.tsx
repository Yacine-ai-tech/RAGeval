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
  { metric: 'Accuracy',                    consensus: '0.800 ★', claude: '0.780', groq: '0.767' },
  { metric: 'Precision',                   consensus: '0.826',   claude: '—',     groq: '—'     },
  { metric: 'Recall',                      consensus: '0.760',   claude: '—',     groq: '—'     },
  { metric: 'F1',                          consensus: '0.792 ★', claude: '—',     groq: '—'     },
  { metric: 'ROC-AUC (raw consensus score)', consensus: '0.880 ★', claude: '—',  groq: '—'     },
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
              <span className="font-medium text-body">Judges:</span> Claude Haiku 4.5 + Groq Llama-3.3-70B (the configured{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">JUDGE_MODELS</code>).
            </li>
            <li>
              <span className="font-medium text-body">Decision threshold:</span> consensus ≥ 0.6 → &ldquo;grounded&rdquo;.
            </li>
            <li>
              <span className="font-medium text-body">N:</span>{' '}
              <span className="num">25</span> questions → <span className="num font-semibold">50</span> labelled examples (balanced).
            </li>
            <li>
              <span className="font-medium text-body">Reproduce:</span>{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">
                python eval/run_judge_benchmark.py --n 25
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
                  <th className="pb-2 text-right">Groq Llama (solo)</th>
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
              <span className="font-semibold text-body">Headline:</span> multi-judge consensus (0.80) beats every individual judge
              (0.78 / 0.767) — the core thesis, measured on a standard dataset. ROC-AUC 0.880 shows the raw consensus
              score cleanly separates grounded from hallucinated answers.
            </p>
            <p className="mt-2">
              <span className="font-semibold text-body">Honest caveat:</span> judge-disagreement (stdev) as an error predictor
              was only marginal here (0.173 on wrong predictions vs 0.170 on correct) — directionally right but not a strong
              signal at N=50; the <code className="rounded bg-surface px-1 py-0.5 text-xs">flag_for_review</code> heuristic
              needs a larger labelled set + threshold tuning before it can be claimed as a reliable hallucination alarm.
            </p>
          </div>
        </Card>

        {/* Scaling */}
        <Card title="Scaling">
          <p className="text-sm text-dim leading-6">
            N=25 keeps the run cheap (~100 judge calls, ~$0.10). Raising{' '}
            <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">--n</code> to a few hundred gives tighter CIs;
            adding a 3rd judge (e.g. GPT-4o-mini, key permitting) tests whether consensus keeps improving.
          </p>
        </Card>
      </div>
    </div>
  );
}
