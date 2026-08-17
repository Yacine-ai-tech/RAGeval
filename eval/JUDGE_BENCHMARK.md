# RAGeval — Multi-Judge Consensus Benchmark (HaluEval)

Research-grade validation of RAGeval's multi-judge groundedness consensus on **HaluEval** (Li et
al., 2023), a standard hallucination-detection benchmark. Reproducible:
`python eval/run_judge_benchmark.py --n 25` (needs `ANTHROPIC_API_KEY` and/or `GROQ_API_KEY`, plus
the `datasets` and `scikit-learn` packages).

This is a small-N sanity check, not a large-scale peer-reviewed study — treat the numbers below as
directionally informative rather than statistically definitive. See the caveats section for what
this run does and does not establish.

## Setup

- **Dataset:** HaluEval-QA. Each question yields **2 labelled examples** against the same
  `knowledge` context: the `right_answer` (grounded = 1) and the `hallucinated_answer`
  (grounded = 0).
- **Judges configured:** the project's current default four-judge `JUDGE_MODELS` (see
  `.env.example`) — Claude Haiku 4.5, Groq `gpt-oss-120b`, Gemini Flash, GPT-4o-mini.
  **What actually responded in this run** differed per judge, and that variance is itself
  reported rather than smoothed over: Claude Haiku 4.5 and Groq `gpt-oss-120b` answered all
  50 examples; Gemini Flash answered the first 7 before hitting its free-tier daily request
  quota (a real, externally-imposed limit, not a code fault) and was skipped for the rest;
  GPT-4o-mini had no API key configured in this run's environment and was skipped for all
  50. This is the actual production consensus behavior — RAGeval never substitutes a
  different judge or fails the whole call when one judge is unavailable, it scores from
  however many of the configured judges (minimum 2) actually respond per call — exercised
  here by real, uncontrived API conditions rather than a mocked scenario.
- **Decision threshold:** consensus score ≥ 0.6 → classified "grounded".
- **Sample size:** N = 25 questions → **50 labelled examples** (balanced 25/25 grounded vs
  hallucinated by construction).

## Results (real run)

| Metric | Consensus (2–3 judges/example) | Claude Haiku 4.5 (solo, n=50) | Groq gpt-oss-120b (solo, n=50) | Gemini Flash (solo, n=7) |
|--------|-----------|---------------------|-------------------|-------------------|
| Accuracy | **0.900** | 0.780 | 0.900 | 1.000 |
| Precision | 0.885 | — | — | — |
| Recall | 0.920 | — | — | — |
| F1 | **0.902** | — | — | — |
| ROC-AUC (raw consensus) | **0.936** | — | — | — |

**Headline, stated plainly:** consensus accuracy (0.900) clearly exceeded Claude Haiku 4.5 solo
(0.780), but on this run it *matched* — did not exceed — Groq `gpt-oss-120b` solo, which was
individually strong on this sample. That's a different picture from an earlier run against the
now-deprecated `llama-3.3-70b-versatile`, where consensus beat both individual judges outright,
and it's reported here rather than left out: a stronger individual judge narrows the gap consensus
provides, which is itself a real and useful finding, not just a less flattering one. Gemini Flash's
1.000 accuracy is on only 7 examples (before its quota cut it off) — too small a sample to draw any
conclusion from; it is not evidence Gemini is "the best judge" here. ROC-AUC of 0.936 indicates the
raw (pre-threshold) consensus score separates grounded from hallucinated answers well on this
dataset.

**Honest caveat — judge disagreement as an error signal:** mean judge-disagreement (stdev across
whichever judges responded) was clearly higher on wrong predictions than on correct ones (0.297 vs
0.090) — a more pronounced gap than an earlier run showed (0.173 vs 0.170). Still: N=50 with a
per-example judge count that varies between 2 and 3 is not a controlled setup, so treat this as a
directionally encouraging observation, not a validated result. The `flag_for_review` heuristic that
leans on this signal would need a larger labelled set, a fixed judge count, and proper threshold
tuning before it could be claimed as a reliable hallucination alarm.

**Other limitations worth naming plainly:** this run's judge count varies per example (2 when
Gemini/GPT-4o-mini were unavailable, 3 for the 7 examples Gemini answered) rather than being fixed,
which is a real limitation of *this specific run*, not of the consensus design itself; two judges
is the minimum configuration RAGeval supports, not necessarily the ceiling for consensus quality;
HaluEval-QA is one dataset with its own generation biases (hallucinated answers are synthetically
produced, which may make them easier or harder to catch than naturally occurring hallucinations);
and these results reflect one point in time against specific judge-model versions and provider
quota states, which will drift.

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
— set `JUDGE_MODELS` before rerunning to control the panel. N=25 (50 labelled examples) keeps a
run cheap — on the order of $0.10–0.30 in API costs at current Haiku/Groq/Gemini/mini-tier pricing,
depending on how many of the configured judges actually respond. Raising `--n` to a few hundred
questions, and ensuring all configured judges have working credentials and unexhausted quota for
the full run (unlike the mixed-availability run reported above), would tighten the confidence
intervals considerably and is the most direct way to turn this from a sanity check into a stronger,
properly comparable result — that is a real cost/time tradeoff against a limited budget, not a
technical limitation of the benchmark script itself.
