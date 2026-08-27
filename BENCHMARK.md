# Benchmark Results

This document provides a headline summary of RAGeval's multi-judge groundedness consensus
validation on the HaluEval benchmark. All methodology details, full statistical results,
and honest caveats are in [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) — that
file is the single source of truth; this one is the entry point.

> **Infrastructure / quota note.** An earlier attempt at this benchmark hit a free-tier
> API quota ceiling, leaving two of four judges largely absent. This has been superseded
> by a corrected rerun with all four judges answering every example — see
> [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) for the full account.

---

## HaluEval-QA — N=200 Run, all 4 judges responding (100 questions × 2 labels each)

Reproducible: `python eval/run_judge_benchmark.py --n 100`
(requires `ANTHROPIC_API_KEY` and/or `GROQ_API_KEY`, plus `datasets` and `scikit-learn`)

### Per-judge / consensus results

| Judge / Strategy | Accuracy | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | 0.750 | 0.745 | 0.760 | 0.752 | 200 |
| Groq `gpt-oss-120b` | 0.835 | 0.791 | 0.910 | 0.847 | 200 |
| GPT-5-mini | 0.860 | 0.805 | 0.950 | 0.872 | 200 |
| **Gemini 3.5 Flash** | **0.885** | 0.853 | 0.930 | 0.890 | 200 |
| **Accuracy-weighted consensus (all 4)** | **0.860** | 0.827 | 0.910 | 0.867 | 200 |

**ROC-AUC (consensus score): 0.902** — the raw consensus score separates grounded from
hallucinated answers well, independent of where the 0.6 decision threshold is drawn.

---

## What Actually Responded

This run was executed with all four judge keys populated and no quota exhaustion:
every judge (Claude Haiku 4.5, Groq `gpt-oss-120b`, GPT-5-mini, Gemini 3.5 Flash)
answered all 200 examples. A prior attempt at this benchmark had two of four judges
largely absent due to a free-tier quota ceiling — that run has been superseded by this
one; see [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) for that history.

---

## Key Finding

**Stated plainly:** with the full 4-judge panel responding, the accuracy-weighted
consensus (0.860) matches the second-best individual judge (GPT-5-mini, 0.860) and is
edged out only by the single strongest judge, Gemini 3.5 Flash (0.885). Weighting each
judge by its own measured accuracy keeps the weakest judge (Claude Haiku 4.5, 0.750)
from dragging the consensus down as far as a plain unweighted mean would — but the
panel still does not beat its best individual member outright on this dataset.

The practical case for the panel isn't "highest possible accuracy" — it's fault
tolerance (a usable score if any one judge is unavailable) plus the disagreement
signal below, which no single judge can provide on its own.

**Judge disagreement as an error signal:** mean disagreement (stdev across the 4
judges' scores) was clearly higher on wrong consensus predictions than on correct ones
(0.217 vs 0.082, n=28 wrong / 172 correct) — a real, useful signal for the
`flag_for_review` heuristic.

---

## Further Reading

- [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) — full methodology, raw numbers,
  bootstrap CIs, 2026 landscape context, and concrete next steps
- [`RESEARCH.md`](RESEARCH.md) — why multiple judges, why LLM-as-judge, and where
  RAGeval sits relative to RAGAS, ARES, TruLens, and the broader evaluation landscape
