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

## Rerun: Precision-Weighted Consensus with Variance Penalty (2026-09-23)

A remediation was proposed to replace the plain accuracy-weighted mean above with a
precision-weighted consensus that also subtracts a variance penalty when judges disagree:
`score = Σ w_i · ŷ_i − λ · σ(ŷ)`, weights set to each judge's own measured accuracy.

This was validated by recomputing over the cached per-judge scores already on disk
(`eval/cache/halueval_200_cache.jsonl`) — no new judge calls, zero cost — on the largest
internally-consistent judge lineup found in that cache: a **240-example, 3-judge** subset
(Groq `gpt-oss-120b`, Gemini 3.5 Flash, GPT-5-mini; this particular cached run did not
include the Claude Haiku judge, so it is a different slice from the 200-example, 4-judge
table above, not a refinement of it).

| Strategy | Accuracy | Precision | Recall | F1 | ROC-AUC | n |
|---|---|---|---|---|---|---|
| Plain accuracy-weighted mean (baseline) | 0.817 | — | — | 0.832 | 0.871 | 240 |
| Best individual judge (Gemini 3.5 Flash) | **0.854** | — | — | — | — | 240 |
| **Precision-weighted + variance penalty (λ=0.15–0.30)** | **0.838** | 0.805 | 0.892 | 0.846 | 0.871 | 240 |

**Honest result:** the new formula is a real improvement over the plain mean (+2.1 points,
0.817 → 0.838) and confirms the disagreement signal (mean judge-score stdev: 0.158 on wrong
predictions vs. 0.026 on correct ones, an even sharper split than the 4-judge panel above).
It does **not**, however, clear the originally proposed >0.895 target, and the panel still
does not beat its single best member (Gemini, 0.854) on this subset — the same
fault-tolerance argument made above for the 4-judge panel applies here too.

---

## Rerun: Cascade/Escalation Strategy — Why Consensus Trails the Best Judge (2026-09-23)

Rather than continue tuning the blending formula, a cascade/escalation strategy was tested —
the pattern production LLM-as-judge pipelines actually lean on: trust the single strongest
judge (Gemini 3.5 Flash) by default, and escalate to the full panel only on genuine
uncertainty. Full reasoning in [`RESEARCH.md`](RESEARCH.md#why-multiple-judges-not-one).

Two escalation signals were tested against the same cached 240-example, 3-judge subset:

| Escalation signal | Cases escalated | Accuracy |
|---|---|---|
| Gemini alone, no escalation | 0 / 240 | **0.854** |
| Escalate when Gemini's own score nears the 0.6 threshold | 0–2 / 240 (rarely triggers — scores are mostly confidently binary) | 0.854–0.858 |
| Escalate when panel disagreement (stdev) exceeds a threshold | 21–33 / 240, depending on threshold | 0.817 (worse at every threshold that actually escalates) |

**Finding: escalating to the panel on disagreement cases makes accuracy worse, not better.**
On the specific 28 cases where the panel disagreed most (judge-score stdev > 0.15), Gemini
alone was still correct **78.6%** of the time (22/28) — its edge over the other two judges is
large and consistent enough that blending in their verdicts pulls more correct answers toward
wrong ones than it catches genuine Gemini errors. Every escalation-band setting tested matched
or underperformed simply trusting Gemini unconditionally.

**Conclusion:** for this specific 3-judge lineup and dataset, no arithmetic combination of the
judges' scores — plain mean, accuracy-weighted, variance-penalized, or disagreement-gated
cascade — beats reporting Gemini's score directly. This is the documented, expected outcome
when one judge in a panel is reliably stronger than the others (see `RESEARCH.md` for the
full literature-grounded reasoning). The panel's disagreement signal remains genuinely useful
as a **human-review escalation trigger** — it correctly flags where the blended score is more
likely wrong — just not as an input folded back into a combined score.

---

## Rerun: Geometric Median and a Heterogeneous (Non-LLM) Judge (2026-09-23)

Two literature-backed alternatives were implemented as opt-in aggregation strategies (see
`RESEARCH.md` for the full literature review and why both default off) and measured against
the same 240-example, 3-judge cached subset used above.

**Geometric median** (RoPoLL, Acharya et al. 2026 — reduces to the classical weighted median
for RAGeval's scalar-score case): a tuning-free, breakdown-point-1/2 robust replacement for
the weighted mean.

**Symbolic/deterministic judge** (`score_symbolic_groundedness`, Independence-Aware
Heterogeneous Evaluation): a $0, non-LLM verification signal — numeric-fact consistency
(does every number the answer states appear in the retrieved context?) plus lexical overlap
— added as a structurally independent 4th panel member.

| Configuration | Accuracy | ROC-AUC |
|---|---|---|
| Gemini alone (reference) | **0.8542** | — |
| Weighted mean, 3 LLM judges (baseline) | 0.8167 | 0.8709 |
| Weighted mean + symbolic judge | 0.8208 | **0.9191** |
| Geometric median, 3 LLM judges | 0.8167 | 0.8256 |
| Geometric median + symbolic judge | 0.8167 | 0.8256 |
| Symbolic judge alone | 0.5625 | — |

**Findings:**
- **Geometric median does not close the gap to Gemini alone** — confirming, on this
  dataset, the "Nine Judges, Two Effective Votes" (Kohli, 2026) claim that this is a
  correlated-judges ceiling rather than a combining-formula problem: a more robust formula
  over the *same* correlated judges still can't out-perform the strongest one.
- **The symbolic judge alone is weak** (0.5625) — HaluEval-QA's hallucinations are mostly
  invented facts/entities, not wrong numbers, so a numeric-consistency check has limited
  reach on this particular dataset.
- **But folding it into the weighted-mean panel meaningfully improves ROC-AUC** (0.8709 →
  0.9191) — a real, structural gain from adding a genuinely uncorrelated signal, distinct
  from anything the same-genre reweighting/cascade experiments above achieved. Raw
  accuracy-at-threshold barely moves and still trails Gemini alone, so this is a partial,
  honest result: real evidence that heterogeneous verification helps, not yet enough to
  change which score should be reported as primary.

**Both are shipped as opt-in, not new defaults** (`RAGEVAL_AGGREGATION_STRATEGY=
geometric_median`, `RAGEVAL_INCLUDE_SYMBOLIC_JUDGE=true`) — turning either on changes every
existing deployment's consensus number, which shouldn't happen silently on an upgrade.

---

## Further Reading

- [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) — full methodology, raw numbers,
  bootstrap CIs, 2026 landscape context, and concrete next steps
- [`RESEARCH.md`](RESEARCH.md) — why multiple judges, why LLM-as-judge, and where
  RAGeval sits relative to RAGAS, ARES, TruLens, and the broader evaluation landscape
