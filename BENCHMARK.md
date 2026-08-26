# Benchmark Results

This document provides a headline summary of RAGeval's multi-judge groundedness consensus
validation on the HaluEval benchmark. All methodology details, full statistical results,
and honest caveats are in [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) — that
file is the single source of truth; this one is the entry point.

> **Infrastructure / quota note.** This benchmark was run against free-tier API keys.
> Two of the four configured judges (Gemini Flash, GPT-4o-mini) were either quota-limited
> or unconfigured during the run — see the "What actually responded" section below and
> the full account in [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md).

---

## HaluEval-QA — N=200 Run (100 questions × 2 labels each)

Reproducible: `python eval/run_judge_benchmark.py --n 100`
(requires `ANTHROPIC_API_KEY` and/or `GROQ_API_KEY`, plus `datasets` and `scikit-learn`)

### Consensus results (with 95% bootstrap confidence intervals)

| Metric | Consensus | 95% CI |
|---|---|---|
| **Accuracy** | **0.785** | [0.725, 0.840] |
| Precision | 0.782 | [0.699, 0.857] |
| Recall | 0.790 | [0.705, 0.865] |
| F1 | **0.786** | [0.717, 0.843] |
| **ROC-AUC** (raw consensus score) | **0.870** | [0.818, 0.915] |

### Per-judge breakdown

| Judge | Accuracy | 95% CI | n answered |
|---|---|---|---|
| Claude Haiku 4.5 | 0.745 | [0.685, 0.805] | 200 |
| Groq `gpt-oss-120b` | **0.830** | [0.775, 0.880] | 200 |
| Gemini Flash | 0.889 | [0.667, 1.000] | **9** — quota-limited |
| GPT-4o-mini | — | — | **0** — no key configured |

---

## What Actually Responded (Quota Reality)

The run was executed against free-tier API keys:

- **Claude Haiku 4.5** and **Groq `gpt-oss-120b`**: answered all 200 examples.
- **Gemini Flash**: hit provider-side `503` errors and then `429` daily-quota exhaustion
  early in the run — succeeded on only 9 of 201 calls.
- **GPT-4o-mini**: no API key was configured for this run — answered 0 examples.

In practice this run's consensus is a **Claude + Groq average** for the large majority
of examples. The "4-judge panel" was never tested with all four judges simultaneously
due to quota constraints — not a design or code limitation.

---

## Key Finding

**Stated plainly:** at N=200, consensus (0.785) did **not** beat the strongest individual
judge. Groq `gpt-oss-120b` solo (0.830, tight CI, full n=200) outperformed the
multi-judge average. The mechanism: RAGeval's current consensus is an unweighted mean,
and averaging in Claude Haiku 4.5 (0.745) pulls the result below Groq's solo accuracy.

This is a real, useful finding about the **current unweighted aggregation method** — not
about the value of multi-judge evaluation per se. ROC-AUC of 0.870 shows the raw
consensus score separates grounded from hallucinated answers well; it is specifically
the threshold-based majority-mean that a single strong judge currently beats.

**Judge disagreement as an error signal:** mean disagreement (stdev across responding
judges) was clearly higher on wrong predictions than on correct ones (0.272 vs 0.069,
n=43 wrong / 157 correct) — a real, useful signal for the `flag_for_review` heuristic.

---

## Further Reading

- [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) — full methodology, raw numbers,
  bootstrap CIs, 2026 landscape context, and concrete next steps
- [`RESEARCH.md`](RESEARCH.md) — why multiple judges, why LLM-as-judge, and where
  RAGeval sits relative to RAGAS, ARES, TruLens, and the broader evaluation landscape
