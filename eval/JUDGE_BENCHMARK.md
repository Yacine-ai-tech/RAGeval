# RAGeval — Multi-Judge Consensus Benchmark (HaluEval)

Research-grade validation of RAGeval's multi-judge groundedness consensus on **HaluEval** (Li et
al., 2023), a standard hallucination-detection benchmark. Reproducible:
`python eval/run_judge_benchmark.py --n 100` (needs `ANTHROPIC_API_KEY` and/or `GROQ_API_KEY`,
plus the `datasets` and `scikit-learn` packages).

The results below are from a real N=200 run (100 questions) with bootstrap 95% confidence
intervals — a meaningful step up in statistical power from an earlier N=50 sanity check, and the
numbers changed in an important way when the sample got bigger (see Headline below). Treat this as
a solid, real result at moderate scale, not yet a large-scale peer-reviewed benchmark — see the
caveats section for exactly what it does and doesn't establish.

## Setup

- **Dataset:** HaluEval-QA. Each question yields **2 labelled examples** against the same
  `knowledge` context: the `right_answer` (grounded = 1) and the `hallucinated_answer`
  (grounded = 0).
- **Judges configured:** a four-judge `JUDGE_MODELS` panel — Claude Haiku 4.5, Groq
  `gpt-oss-120b`, Gemini Flash, GPT-4o-mini. (Note: `.env.example`'s shipped default panel has
  since narrowed to three judges — Claude Haiku 4.5, Groq `gpt-oss-120b`, GPT-5-mini — with no
  Gemini entry; this run predates that change and reflects the four-judge configuration in place
  at the time, not today's shipped default.)
  **What actually responded, reported exactly as it happened:** Claude Haiku 4.5 and Groq
  `gpt-oss-120b` answered all 200 examples. Gemini Flash was unreliable essentially from the
  start of the run, not cleanly "working then cutting off" — provider-side `503` ("model
  experiencing high demand") errors and occasional dropped connections appeared within the
  first few examples, then `429` daily-quota exhaustion joined in and dominated for the rest.
  Across the run (200 examples, one of which needed a retry), Gemini was called 201 times and
  succeeded only **9 times** (192 failed calls, scattered mostly in the earlier portion of the
  run, not a clean block). GPT-4o-mini had no API key
  configured in this run's environment and answered 0. This is the actual production consensus
  behavior — RAGeval never substitutes a different judge or fails the whole call when one is
  unavailable, it scores from however many of the configured judges (minimum 2) actually respond
  per call. In practice this run's consensus is a Claude+Groq average for the large majority of
  examples, with Gemini contributing a small, scattered amount of extra signal on 9 of them.
- **Decision threshold:** consensus score ≥ 0.6 → classified "grounded".
- **Sample size:** N = 100 questions → **200 labelled examples** (balanced 100/100 grounded vs
  hallucinated by construction). Zero examples were skipped or failed.

## Results (real run, N=200, with 95% bootstrap CIs)

| Metric | Consensus | 95% CI |
|--------|-----------|--------|
| Accuracy | **0.785** | [0.725, 0.840] |
| Precision | 0.782 | [0.699, 0.857] |
| Recall | 0.790 | [0.705, 0.865] |
| F1 | **0.786** | [0.717, 0.843] |
| ROC-AUC (raw consensus) | **0.870** | [0.818, 0.915] |

| Judge (solo) | Accuracy | 95% CI | n |
|--------------|----------|--------|---|
| Claude Haiku 4.5 | 0.745 | [0.685, 0.805] | 200 |
| Groq `gpt-oss-120b` | **0.830** | [0.775, 0.880] | 200 |
| Gemini Flash | 0.889 | [0.667, 1.000] | 9 |

**Headline, stated plainly — this is the important finding, not a footnote:** at N=200,
**consensus (0.785 accuracy) did not beat the strongest individual judge.** Groq `gpt-oss-120b`
solo (0.830, tight CI on a full n=200) outperformed the multi-judge average outright. This is a
materially different, more informative result than an earlier, smaller N=50 run, where consensus
had appeared to match or beat every individual judge — a good demonstration of exactly why that
earlier result was flagged as directionally suggestive rather than conclusive, and why N mattered
here. The mechanism is straightforward: RAGeval's consensus is an unweighted mean across whichever
judges respond, and Claude Haiku 4.5 was the meaningfully weaker judge on this dataset (0.745 vs
Groq's 0.830) — averaging in a weaker judge pulls the consensus below the strongest individual
judge's accuracy. Gemini's 0.889 is on only 9 examples (CI spans [0.667, 1.000]) — not a reliable
estimate, and not evidence Gemini is "the best judge" here. ROC-AUC of 0.870 still shows the raw
consensus score separates grounded from hallucinated answers well; it's specifically the
threshold-1 majority-mean aggregation that a single strong judge currently beats.

**What this means for the design, honestly:** unweighted averaging is not automatically better
than the best available single judge — that's a real, useful negative result about the current
aggregation method, not about the value of using multiple judges per se. A different aggregation
strategy (e.g. weighting judges by their own measured accuracy, or a majority vote requiring
agreement rather than an arithmetic mean) might recover or exceed the best-single-judge accuracy
while keeping the "no unverified single point of failure" and disagreement-flagging properties
that motivate using more than one judge in the first place — but that's a real design change this
benchmark surfaces the need for, not something already implemented and validated here.

**Judge disagreement as an error signal:** mean judge-disagreement (stdev across whichever judges
responded) was clearly higher on wrong predictions than on correct ones (0.272 vs 0.069, n=43
wrong / 157 correct) — consistent in direction with a smaller earlier run, and now backed by a
larger sample. This remains a real, useful prior for the `flag_for_review` heuristic, though
turning it into a calibrated detector (a precision/recall curve for "should this be flagged", not
just a directional mean-difference) is still unvalidated future work.

**Other limitations worth naming plainly:** this remains a single dataset (HaluEval-QA has its own
generation biases — hallucinated answers are synthetically constructed, which may make them easier
or harder to catch than naturally occurring hallucinations); Gemini and GPT-4o-mini's near-total
absence from this run means the reported "consensus" is really a 2-judge result in practice, not a
true test of the full 4-judge configuration; and this reflects one point in time against specific
judge-model versions and provider quota states, which will drift — including the panel composition
itself, which has already changed once (see the shipped-default note in Setup above) since this run.

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
— set `JUDGE_MODELS` before rerunning to control the panel. The N=200 run above cost well under
$1 in API charges (Claude Haiku 4.5 and Groq `gpt-oss-120b` are both inexpensive per-token, and
Gemini/GPT-4o-mini contributed almost nothing to the bill given how little they responded) — cost
is not the limiting factor at this scale. What *would* meaningfully improve on this result:

- **Getting GPT-4o-mini and a non-quota-exhausted Gemini into the same run**, so the reported
  consensus reflects the full configured 4-judge panel rather than being dominated by 2 judges.
- **Testing a non-uniform aggregation** (e.g. accuracy-weighted averaging, or majority vote with a
  minimum-agreement threshold) against this same labelled set, directly motivated by this run's
  finding that unweighted averaging underperforms the single best judge.
- **A second dataset** (RAGTruth or a hand-labeled sample from real production traffic) to check
  whether the judge-strength ordering seen here (Groq > Gemini > Claude Haiku on this sample) holds
  outside HaluEval's specific hallucination-construction method.

None of that is committed or scheduled — it's the concrete next step this specific result points
to, stated plainly rather than left implicit.
