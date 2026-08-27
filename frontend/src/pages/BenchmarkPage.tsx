import React from 'react';
import { PageHeader } from '../kit/AppShell';
import { Card } from '../kit/primitives';

// Benchmark results are rendered as actual React components (tables, headings,
// code blocks) instead of a raw <pre> dump of a Markdown string.

interface TableRow {
  judge: string;
  accuracy: string;
  precision: string;
  recall: string;
  f1: string;
  n: string;
}

const RESULTS: TableRow[] = [
  { judge: 'Claude Haiku 4.5',                     accuracy: '0.750',   precision: '0.745', recall: '0.760', f1: '0.752', n: '200' },
  { judge: 'Groq gpt-oss-120b',                     accuracy: '0.835',   precision: '0.791', recall: '0.910', f1: '0.847', n: '200' },
  { judge: 'GPT-5-mini',                            accuracy: '0.860',   precision: '0.805', recall: '0.950', f1: '0.872', n: '200' },
  { judge: 'Gemini 3.5 Flash ★',                     accuracy: '0.885',   precision: '0.853', recall: '0.930', f1: '0.890', n: '200' },
  { judge: 'Accuracy-weighted consensus (all 4)',   accuracy: '0.860',   precision: '0.827', recall: '0.910', f1: '0.867', n: '200' },
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
              <span className="font-medium text-body">Judges configured:</span> a four-judge{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">JUDGE_MODELS</code> panel — Claude Haiku 4.5, Groq{' '}
              <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">gpt-oss-120b</code>, GPT-5-mini, and Gemini 3.5 Flash.{' '}
              <span className="font-medium text-body">What actually responded:</span> all four judges answered all
              200 examples — no quota exhaustion during this run. An earlier attempt at this benchmark had two of
              four judges largely absent due to a free-tier quota ceiling; this run supersedes that one. RAGeval
              never substitutes a different judge or fails the whole call when one is unavailable — it scores from
              however many of the configured judges (minimum 2) actually respond, weighted by each judge's own
              measured accuracy.
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
        <Card title="Results (real run, N=200, all 4 judges responding)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[11px] font-medium uppercase tracking-wide text-muted">
                  <th className="pb-2 pr-6">Judge / Strategy</th>
                  <th className="pb-2 pr-6 text-right">Accuracy</th>
                  <th className="pb-2 pr-6 text-right">Precision</th>
                  <th className="pb-2 pr-6 text-right">Recall</th>
                  <th className="pb-2 text-right">F1</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {RESULTS.map((row) => (
                  <tr key={row.judge}>
                    <td className="py-2.5 pr-6 text-dim">{row.judge}</td>
                    <td className="num py-2.5 pr-6 text-right font-semibold text-body">{row.accuracy}</td>
                    <td className="num py-2.5 pr-6 text-right text-muted">{row.precision}</td>
                    <td className="num py-2.5 pr-6 text-right text-muted">{row.recall}</td>
                    <td className="num py-2.5 text-right text-muted">{row.f1}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 rounded-xl border border-line bg-surface-2 p-4 text-[13px] leading-6 text-dim">
            <p>
              <span className="font-semibold text-body">Headline:</span> with the full 4-judge panel responding,
              the accuracy-weighted consensus (0.860) matches the second-best individual judge — GPT-5-mini (0.860)
              — and is edged out only by the single strongest judge, Gemini 3.5 Flash (0.885). Weighting each judge
              by its own measured accuracy keeps the weakest judge, Claude Haiku 4.5 (0.750), from dragging the
              consensus down as far as a plain unweighted mean would — but the panel still doesn't beat its best
              individual member outright on this dataset. ROC-AUC 0.902 shows the raw consensus score separates
              grounded from hallucinated answers well, independent of where the 0.6 decision threshold is drawn.
            </p>
            <p className="mt-2">
              <span className="font-semibold text-body">Honest caveat:</span> this is a real, moderate-scale result
              (N=200), not yet a large-scale peer-reviewed benchmark. The practical case for the panel isn't
              "highest possible accuracy" — it's fault tolerance (a usable score if any one judge is unavailable)
              plus the disagreement signal (mean stdev 0.217 on wrong predictions vs 0.082 on correct ones), which
              no single judge can provide on its own. The judge weights are themselves derived from accuracy
              measured on this same dataset, so the weighted-consensus number isn't fully independent of the
              per-judge numbers it's being compared against.
            </p>
          </div>
        </Card>

        {/* Scaling */}
        <Card title="Scaling">
          <p className="text-sm text-dim leading-6">
            N=100 (200 labelled examples) keeps the run cheap — all four judges are inexpensive per-token at this
            volume; the full run costs well under $1. What would meaningfully improve on this result: a stricter
            aggregation strategy (majority vote with a minimum-agreement threshold, or weights recalibrated on a
            held-out split rather than the same data being reported on); a second, RAG-specific dataset (e.g.
            RAGTruth) to check whether the judge-strength ordering seen here holds elsewhere; and repeating this
            run periodically, since provider quota availability and panel composition are not guaranteed to stay
            this favorable.
          </p>
        </Card>
      </div>
    </div>
  );
}
