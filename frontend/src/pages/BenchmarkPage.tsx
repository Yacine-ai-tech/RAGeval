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
  { metric: 'Accuracy',                    consensus: '0.785',   claude: '0.745', groq: '0.830 ★' },
  { metric: 'Precision',                   consensus: '0.782',   claude: '—',     groq: '—'       },
  { metric: 'Recall',                      consensus: '0.790',   claude: '—',     groq: '—'       },
  { metric: 'F1',                          consensus: '0.786',   claude: '—',     groq: '—'       },
  { metric: 'ROC-AUC (raw consensus score)', consensus: '0.870 ★', claude: '—',  groq: '—'       },
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
              <span className="font-medium text-body">Judges configured:</span> this run used a four-judge{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">JUDGE_MODELS</code> panel — Claude Haiku 4.5, Groq{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">gpt-oss-120b</code>, Gemini Flash, GPT-4o-mini.
              The shipped default panel has since narrowed to three judges (Claude Haiku 4.5, Groq{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">gpt-oss-120b</code>, GPT-5-mini — no Gemini) and
              no longer matches this run's exact configuration.{' '}
              <span className="font-medium text-body">What actually responded:</span> Claude Haiku 4.5 and Groq{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">gpt-oss-120b</code> answered all 200 examples.
              Gemini Flash succeeded on only 9 of 201 calls (provider-side 503s early, then daily-quota 429s for the
              rest); GPT-4o-mini had no API key configured in this run's environment and answered 0. RAGeval never
              substitutes a different judge or fails the whole call when one is unavailable — it scores from however
              many of the configured judges (minimum 2) actually respond. This run's consensus is a Claude+Groq
              average for the large majority of examples, with Gemini contributing scattered extra signal on 9 of them.
            </li>
            <li>
              <span className="font-medium text-body">Decision threshold:</span> consensus ≥ 0.6 → &ldquo;grounded&rdquo;.
            </li>
            <li>
              <span className="font-medium text-body">N:</span>{' '}
              <span className="num">100</span> questions → <span className="num font-semibold">200</span> labelled examples (balanced), with 95% bootstrap confidence intervals.
            </li>
            <li>
              <span className="font-medium text-body">Reproduce:</span>{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">
                python eval/run_judge_benchmark.py --n 100
              </code>{' '}
              (needs <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">ANTHROPIC_API_KEY</code> /{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">GROQ_API_KEY</code>,{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">datasets</code>,{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">scikit-learn</code>).
            </li>
          </ul>
        </Card>

        {/* Results table */}
        <Card title="Results (real run, N=200, with 95% bootstrap CIs)">
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
              <span className="font-semibold text-body">Headline:</span> at N=200, consensus (0.785 accuracy) did not
              beat the strongest individual judge — Groq <code className="rounded bg-surface px-1 py-0.5 text-xs">gpt-oss-120b</code> solo
              (0.830 accuracy, tight CI on a full n=200) outperformed the multi-judge average outright, which in turn
              beat Claude Haiku 4.5 solo (0.745). Consensus is an unweighted mean across whichever judges respond, and
              Claude was the meaningfully weaker judge here — averaging it in pulls the consensus below Groq's solo
              score. Gemini's 0.889 accuracy is on only 9 examples (95% CI [0.667, 1.000]) — not a reliable estimate,
              and not evidence Gemini is "the best judge" here. ROC-AUC 0.870 still shows the raw consensus score
              separates grounded from hallucinated answers well; it's specifically the threshold-mean aggregation that
              a single strong judge currently beats.
            </p>
            <p className="mt-2">
              <span className="font-semibold text-body">Honest caveat:</span> this is a real, moderate-scale result
              (N=200, bootstrap CIs), not yet a large-scale peer-reviewed benchmark. It is a meaningful step up from an
              earlier N=50 sanity check whose numbers looked more favorable to consensus — a good demonstration of why
              sample size mattered here. Unweighted averaging losing to the best single judge is itself evidence the
              aggregation method, not just the judge count, needs work before{' '}
              <code className="rounded bg-surface px-1 py-0.5 text-xs">flag_for_review</code> can be called a reliable
              hallucination alarm.
            </p>
          </div>
        </Card>

        {/* Scaling */}
        <Card title="Scaling">
          <p className="text-sm text-dim leading-6">
            N=100 (200 labelled examples) still keeps the run cheap — Claude Haiku and Groq{' '}
            <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">gpt-oss-120b</code> are both inexpensive
            per-token. Raising <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">--n</code> further would
            tighten confidence intervals more; getting GPT-4o-mini and a non-quota-exhausted Gemini into the same run
            would test the full four-judge configuration this run intended, instead of the 2 judges (plus a handful of
            Gemini responses) that actually carried it.
          </p>
        </Card>
      </div>
    </div>
  );
}
