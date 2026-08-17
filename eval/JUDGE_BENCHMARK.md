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
- **Judges (at the time of this run):** Claude Haiku 4.5 + Groq Llama-3.3-70B (the
  `JUDGE_MODELS` configured when these numbers were produced). **Note:** Groq later
  deprecated `llama-3.3-70b-versatile`; the project's current default `JUDGE_MODELS`
  (see `.env.example`) uses `groq/openai/gpt-oss-120b` in its place, alongside Gemini
  Flash and GPT-4o-mini as additional judges. The numbers below reflect the two-judge
  config actually run, not today's default four-judge config — re-run
  `python eval/run_judge_benchmark.py --n 25` against your own `.env` to get numbers for
  your current judge set; results will differ with a different judge count/mix.
- **Decision threshold:** consensus score ≥ 0.6 → classified "grounded".
- **Sample size:** N = 25 questions → **50 labelled examples** (balanced 25/25 grounded vs
  hallucinated by construction).

## Results (real run)

| Metric | Consensus | Claude Haiku (solo) | Groq Llama (solo) |
|--------|-----------|---------------------|-------------------|
| Accuracy | **0.800** | 0.780 | 0.767 |
| Precision | 0.826 | — | — |
| Recall | 0.760 | — | — |
| F1 | **0.792** | — | — |
| ROC-AUC (raw consensus) | **0.880** | — | — |

**Headline:** on this sample, multi-judge **consensus (0.80 accuracy) edges out every individual
judge** (0.78 / 0.767) — consistent with the project's core design thesis, though the margin is
modest and N=50 is small enough that this should be read as suggestive, not conclusive. ROC-AUC of
0.880 indicates the raw (pre-threshold) consensus score separates grounded from hallucinated
answers reasonably well on this dataset.

**Honest caveat — judge disagreement as an error signal:** mean judge-disagreement (stdev across
judges) was only marginally higher on wrong predictions than on correct ones (0.173 vs 0.170) —
directionally in the expected direction, but not a strong or statistically robust signal at
N=50. The `flag_for_review` heuristic that leans on this signal would need a larger labelled set
and proper threshold tuning before it could be claimed as a reliable hallucination alarm; right now
treat it as a weak prior, not a detector.

**Other limitations worth naming plainly:** two judges is the minimum configuration RAGeval
supports, not necessarily the ceiling for consensus quality; HaluEval-QA is one dataset with its
own generation biases (hallucinated answers are synthetically produced, which may make them easier
or harder to catch than naturally occurring hallucinations); and these results reflect one point in
time against specific judge-model versions, which will drift as providers update their models.

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
threshold, default 0.6). N=25 (50 labelled examples, ~100 judge calls total across 2 judges) keeps
a run cheap — roughly $0.10 in API costs at current Haiku/Llama pricing. Raising `--n` to a few
hundred questions would tighten the confidence intervals on these metrics considerably and is the
most direct way to turn this from a sanity check into a stronger result. Adding a third judge (for
example an OpenAI mini-tier model, API key permitting) means setting a three-model `JUDGE_MODELS`
list in config before rerunning — the script itself doesn't take a judges flag, it just reports
whatever judges the configured `RAGEvaluator` actually calls — and would test whether consensus
accuracy keeps improving as panel size grows, per the panel-of-judges literature referenced above.
