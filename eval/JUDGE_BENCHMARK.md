# RAGeval — Multi-Judge Consensus Benchmark (HaluEval)

Research-grade validation of RAGeval's multi-judge groundedness consensus on **HaluEval** (Li et
al., 2023), a standard hallucination-detection benchmark. Reproducible:
`python eval/run_judge_benchmark.py --n 100` (needs `ANTHROPIC_API_KEY` and/or `GROQ_API_KEY`,
plus the `datasets` and `scikit-learn` packages).

The results below are from a real N=200 run (100 questions) with all four configured judges
responding to every example — a corrected, complete rerun of an earlier attempt where two of the
four judges were largely absent (see "What changed since the first attempt" below). Treat this as
a solid, real result at moderate scale, not yet a large-scale peer-reviewed benchmark — see the
caveats section for exactly what it does and doesn't establish.

## Setup

- **Dataset:** HaluEval-QA. Each question yields **2 labelled examples** against the same
  `knowledge` context: the `right_answer` (grounded = 1) and the `hallucinated_answer`
  (grounded = 0).
- **Judges configured:** a four-judge `JUDGE_MODELS` panel — Claude Haiku 4.5 (routed via
  OpenAI-compatible inference proxy, `openai/anthropic/claude-haiku-4-5-20251001`), Groq
  `gpt-oss-120b`, Gemini 3.5 Flash (`gemini/gemini-3.5-flash`, direct Gemini API key), and
  GPT-5-mini (via OpenAI-compatible inference proxy, `openai/gpt-5-mini`). Earlier runs used
  `gemini-flash-latest` (deprecated) and `gpt-4o-mini` (not available on the proxy in use) — both
  have since been replaced with their current, working equivalents without changing the panel's
  intended diversity (fast/cheap, strong/OSS, Google, OpenAI tiers).
- **Decision threshold:** consensus score ≥ 0.6 → classified "grounded".
- **Sample size:** N = 100 questions → **200 labelled examples** (balanced 100/100 grounded vs
  hallucinated by construction). Zero examples were skipped or failed in this run.
- **Consensus strategy:** `RAGEvaluator.score_groundedness_consensus` computes an accuracy-weighted
  mean across whichever judges respond for a given example (not a simple unweighted average).

### What changed since the first attempt

The first N=200 attempt at this benchmark hit a free-tier API quota ceiling partway through:
Claude Haiku 4.5 and Groq `gpt-oss-120b` answered all 200 examples, but Gemini hit provider-side
`503` (high demand) and `429` (daily-quota exhaustion) errors on all but 9 of 201 calls, and
GPT-4o-mini had no working key configured in that run's environment at all. That run's reported
"4-judge consensus" was, in practice, dominated by 2 judges.

This run was re-executed with all four judge keys populated and no quota exhaustion during the
run: every judge answered all 200 examples. The results below reflect the genuine 4-judge panel.

## Results (real run, N=200, all 4 judges responding)

| Judge / Strategy | Accuracy | Precision | Recall | F1 | n |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | 0.750 | 0.745 | 0.760 | 0.752 | 200 |
| Groq `gpt-oss-120b` | 0.835 | 0.791 | 0.910 | 0.847 | 200 |
| GPT-5-mini | 0.860 | 0.805 | 0.950 | 0.872 | 200 |
| **Gemini 3.5 Flash** | **0.885** | 0.853 | 0.930 | 0.890 | 200 |
| **Weighted consensus (all 4)** | **0.860** | 0.827 | 0.910 | 0.867 | 200 |

**ROC-AUC (consensus score):** 0.902 — the raw consensus score separates grounded from
hallucinated answers well, independent of where the 0.6 decision threshold is drawn.

**Headline, stated plainly:** with the full 4-judge panel actually responding, the accuracy-weighted
consensus (0.860) matches the second-best individual judge (GPT-5-mini, 0.860) and is edged out only
by the single strongest judge, Gemini 3.5 Flash (0.885). Weighting by each judge's own measured
accuracy keeps the weaker judge (Claude Haiku 4.5, 0.750) from dragging the consensus down as far as
an unweighted mean would — but it still doesn't let the panel beat its best individual member outright
on this dataset. The practical case for the panel isn't "highest possible accuracy" — it's
fault tolerance (the system keeps producing a usable score if any one judge is unavailable) plus the
disagreement signal below, which no single judge can provide on its own.

### Disagreement predicts errors

Mean judge-disagreement (standard deviation across the 4 judges' scores for a given example) is
clearly higher on wrong consensus predictions than on correct ones:

- Mean stdev on **correct** predictions (172/200): `0.082`
- Mean stdev on **wrong** predictions (28/200): `0.217`

Flagging any answer with stdev > 0.2 for human review remains a real, useful heuristic — judges
disagreeing with each other is a meaningful signal that the consensus call is more likely to be
wrong, independent of what the consensus score itself says.

**What this means for the design, honestly:** accuracy-weighted averaging recovers most but not all
of the gap to the single best judge — that's a real, measured result about the current aggregation
method, not about the value of using multiple judges per se. A stricter aggregation strategy (e.g. a
majority vote requiring agreement rather than a weighted mean) might close the remaining gap while
keeping the "no unverified single point of failure" and disagreement-flagging properties that
motivate using more than one judge in the first place — but that's a further design change this
benchmark surfaces the need for, not something already implemented and validated here.

**Other limitations worth naming plainly:** this remains a single dataset (HaluEval-QA has its own
generation biases — hallucinated answers are synthetically constructed, which may make them easier
or harder to catch than naturally occurring hallucinations); this reflects one point in time against
specific judge-model versions and provider quota states, which will drift — including the panel
composition itself, which has already changed once (see the shipped-default note in Setup above)
since the first attempt at this run; and the judge weights are themselves derived from measured
accuracy on this same dataset, so the weighted-consensus number is not fully independent of the
per-judge accuracy numbers it's being compared against.

## 2026 landscape

For context, and without claiming to be exhaustive: using one LLM to grade another's output
("LLM-as-a-judge") became a widely used evaluation technique following work such as Zheng et al.'s
MT-Bench / Chatbot Arena studies (2023), which showed LLM judges could approximate human preference
judgments at a fraction of the cost of human annotation. A recognized limitation of that approach is
that a single judge model carries its own biases — verbosity bias (rewarding longer answers),
self-preference bias (favoring outputs that resemble its own style), and position bias in pairwise
comparisons are commonly discussed failure modes. Using a panel of several (often smaller/cheaper)
judge models and aggregating their votes, rather than relying on one large judge, is an approach
explored in the research literature under names like "panel of LLM evaluators" or jury-style
ensembling — see, e.g., Verga et al.'s "Replacing Judges with Juries" (2024) for one treatment of
this idea. RAGeval's multi-judge consensus score is a practical application of that general
direction, applied specifically to groundedness/faithfulness scoring in a RAG pipeline rather than
open-ended pairwise preference judging.

On the RAG-evaluation side specifically, HaluEval (used for this benchmark) is one of several
datasets built for hallucination evaluation; RAGTruth and FActScore are other commonly cited
benchmarks/frameworks focused on faithfulness and factual precision, using somewhat different
methodologies (RAGTruth focuses on span-level hallucination annotation in RAG outputs; FActScore
decomposes generated text into atomic facts and checks each against a knowledge source). In the
tooling space, RAGAS and ARES are established open-source frameworks purpose-built for evaluating
RAG pipelines, and a broader category of LLM-observability platforms — projects and companies such
as Langfuse, Arize Phoenix, TruLens, DeepEval, Galileo, and Patronus AI — cover adjacent ground
(tracing, cost tracking, eval-metric dashboards) with varying degrees of overlap with RAGeval's
scope. This benchmark doesn't attempt a head-to-head comparison against any of that tooling; it's
narrowly scoped to validating RAGeval's own consensus-vs-solo-judge design choice on one dataset.

## Scaling / reproducing

`run_judge_benchmark.py` accepts `--n` (question count, default 25) and `--threshold` (decision
threshold, default 0.6); it reports whatever judges the configured `RAGEvaluator` actually calls
— set `JUDGE_MODELS` before rerunning to control the panel. The N=200 run above cost well under $1
in API charges (all four judges are inexpensive per-token at this volume) — cost is not the
limiting factor at this scale; provider-side rate limits and daily quota ceilings on free-tier keys
are the practical constraint on running this larger or more often. What *would* meaningfully improve
on this result:

- **A stricter aggregation strategy** (e.g. majority vote with a minimum-agreement threshold, or
  weights recalibrated on a held-out split rather than the same data being reported on) tested
  against this same labelled set, directly motivated by this run's finding that weighted averaging
  still doesn't fully close the gap to the single best judge.
- **A second dataset** (RAGTruth or a hand-labeled sample from real production traffic) to check
  whether the judge-strength ordering seen here (Gemini > GPT-5-mini > Groq > Claude Haiku on this
  sample) holds outside HaluEval's specific hallucination-construction method.
- **Repeating this run periodically**, since the panel composition has already changed once
  (deprecated/unavailable models swapped out) and provider quota availability is not guaranteed to
  be this favorable on every attempt.

None of that is committed or scheduled — it's the concrete next step this specific result points
to, stated plainly rather than left implicit.
