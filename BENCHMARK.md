# Benchmark Results

RAGeval's groundedness-judging component is evaluated against HaluEval-QA, a labeled
hallucination-detection benchmark, comparing individual LLM judges against several methods of
combining them into a consensus score. Full methodology and raw results:
[`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md).

---

## Individual Judges and Baseline Consensus (N=200)

Reproducible via `python eval/run_judge_benchmark.py --n 100` (100 questions × 2 labels each).

| Judge / Strategy | Accuracy | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | 0.750 | 0.745 | 0.760 | 0.752 | 200 |
| Groq `gpt-oss-120b` | 0.835 | 0.791 | 0.910 | 0.847 | 200 |
| GPT-5-mini | 0.860 | 0.805 | 0.950 | 0.872 | 200 |
| **Gemini 3.5 Flash** | **0.885** | 0.853 | 0.930 | 0.890 | 200 |
| Accuracy-weighted consensus (all four) | 0.860 | 0.827 | 0.910 | 0.867 | 200 |

Consensus ROC-AUC: 0.902 — the raw consensus score separates grounded from hallucinated
answers well, independent of the decision threshold.

**Result.** With all four judges responding, the accuracy-weighted consensus (0.860) matches
the second-strongest individual judge and trails the single strongest judge, Gemini 3.5 Flash
(0.885). Weighting each judge by its own measured accuracy keeps the weakest judge from
dragging the consensus down as far as an unweighted mean would, but the panel does not exceed
its strongest individual member on this dataset. Judge disagreement (standard deviation across
the four scores) is a useful secondary signal independent of this: it measures 0.217 on
incorrect consensus predictions versus 0.082 on correct ones (n = 28 incorrect, 172 correct),
supporting its use as a review-flagging heuristic even where it does not improve the blended
score itself.

---

## Alternative Consensus Strategies (N=240, three-judge subset)

Four additional aggregation strategies were evaluated on a 240-example subset (Groq
`gpt-oss-120b`, Gemini 3.5 Flash, GPT-5-mini) to test whether a different combining formula
closes the gap to the single strongest judge.

| Strategy | Accuracy | F1 | ROC-AUC | n |
|---|---|---|---|---|
| Best individual judge (Gemini 3.5 Flash) | **0.854** | — | — | 240 |
| Unweighted mean | 0.817 | 0.832 | 0.871 | 240 |
| Precision-weighted mean with variance penalty | 0.838 | 0.846 | 0.871 | 240 |
| Geometric median (weighted median, scalar case) | 0.817 | — | 0.826 | 240 |
| Escalation cascade (panel disagreement as trigger) | 0.817 | — | — | 240 |

**Precision-weighted consensus with a variance penalty** (`score = Σ wᵢ·ŷᵢ − λ·σ(ŷ)`, weights
set to each judge's measured accuracy) improves on the unweighted mean by 2.1 points (0.817 →
0.838) and sharpens the disagreement-as-error-signal relationship further (judge-score standard
deviation of 0.158 on incorrect predictions versus 0.026 on correct ones). It does not exceed
Gemini alone.

**Geometric median**, a breakdown-point-1/2 robust alternative to the mean (RoPoLL, Acharya et
al. 2026), does not close the gap either — consistent with the "Nine Judges, Two Effective
Votes" (Kohli, 2026) finding that this class of gap reflects correlation among same-genre LLM
judges rather than a weakness in the combining formula.

**Escalation cascade** — trusting Gemini by default and escalating to the full panel only on
signaled uncertainty — was tested against two escalation triggers. Escalating when Gemini's
own score approaches the decision threshold rarely fires, since per-judge scores on this task
are mostly confidently binary. Escalating on panel disagreement fires on 21–33 of 240 cases
depending on threshold, and reduces accuracy to 0.817 at every threshold tested: on the 28
cases where the panel disagreed most, Gemini alone remained correct 78.6% of the time (22/28),
so blending in the other judges' comparatively weaker verdicts moved more correct answers
toward incorrect than it corrected genuine Gemini errors.

**Across every strategy tested** — unweighted mean, accuracy-weighted mean, precision-weighted
mean with a variance penalty, geometric median, and disagreement-gated escalation — none
exceeds the single strongest judge's accuracy on this dataset. This is the documented, expected
outcome when one judge in a panel is reliably stronger than the others; see
[RESEARCH.md](RESEARCH.md) for the supporting literature. The panel's disagreement signal
remains useful as a human-review escalation trigger independent of this result.

---

## Heterogeneous (Non-LLM) Judge and Geometric Median

A deterministic, non-LLM verification signal — numeric-fact consistency between the answer and
retrieved context, plus lexical overlap (`score_symbolic_groundedness`) — was added as a
structurally independent panel member, on the same 240-example subset.

| Configuration | Accuracy | ROC-AUC |
|---|---|---|
| Gemini alone (reference) | 0.8542 | — |
| Weighted mean, three LLM judges | 0.8167 | 0.8709 |
| Weighted mean + symbolic judge | 0.8208 | **0.9191** |
| Geometric median, three LLM judges | 0.8167 | 0.8256 |
| Geometric median + symbolic judge | 0.8167 | 0.8256 |
| Symbolic judge alone | 0.5625 | — |

The symbolic judge alone is weak (0.5625 accuracy) — HaluEval-QA's hallucinations are
predominantly invented facts and entities rather than numeric errors, limiting a
numeric-consistency check's reach on this dataset. Folded into the weighted-mean panel,
however, it raises ROC-AUC from 0.8709 to 0.9191 — a structural improvement in how well the
blended score ranks grounded versus hallucinated answers, from a genuinely uncorrelated
signal rather than a recombination of the same three correlated judges. Accuracy at the fixed
threshold does not move past Gemini alone.

Both the geometric-median strategy and the symbolic judge are opt-in
(`RAGEVAL_AGGREGATION_STRATEGY=geometric_median`, `RAGEVAL_INCLUDE_SYMBOLIC_JUDGE=true`), not
defaults, so adopting either is a deliberate choice for existing deployments rather than a
change on upgrade.

---

## Meta-Judge / Arbiter Panel (N=53)

The strategies above each combine judge scores with a fixed formula. A fifth mechanism —
model arbitration rather than formula combination — was evaluated on HaluEval-QA using Groq
and Gemini directly: each independently scores groundedness with a rationale, then a third,
independent model call is given both scores and rationales, plus the original answer and
context, and produces its own final verdict.

| Score | Accuracy | F1 | ROC-AUC |
|---|---|---|---|
| Groq alone (best single judge) | **0.8868** | **0.8966** | **0.9174** |
| Gemini alone | 0.8113 | 0.8214 | 0.8105 |
| Unweighted mean (Groq, Gemini) | 0.8113 | 0.8214 | 0.9003 |
| Arbiter (third call, sees both judges' verdicts) | 0.8868 | 0.8966 | 0.8846 |

The arbiter matches Groq exactly on accuracy and F1, and trails it on ROC-AUC (0.8846 versus
0.9174) — also below the two-judge mean's ROC-AUC (0.9003). This is the fifth combination
mechanism tested — following unweighted mean, weighted mean with a variance penalty,
geometric median, and a heterogeneous symbolic panel member — that does not exceed the single
strongest judge's raw accuracy on this dataset, consistent with the correlated-judges
explanation cited above.

---

## Further Reading

- [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) — full methodology, raw numbers,
  bootstrap confidence intervals, and the 2026 judge-panel literature landscape
- [`RESEARCH.md`](RESEARCH.md) — the case for LLM-as-judge and multi-judge panels, and how
  RAGeval relates to RAGAS, ARES, TruLens, and the broader evaluation landscape
