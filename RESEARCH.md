# Research Background

This document explains the reasoning behind two of RAGeval's core design choices — using an
LLM as the groundedness/faithfulness judge, and using a panel of judges rather than one — and
situates the project relative to the broader RAG-evaluation research landscape. Empirical
validation of these choices is in [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) and
[`BENCHMARK.md`](BENCHMARK.md).

RAGeval is a practical, applied tool. It draws on established ideas from the LLM-evaluation
literature and applies them to production RAG observability; it does not claim to introduce
novel evaluation methodology of its own.

## Why an LLM Judge, Not Embedding Similarity Alone

A common, low-cost way to approximate "is this answer grounded in the retrieved context?" is
embedding similarity between the answer and the context chunks. RAGeval uses this signal too,
for retrieval relevance and as a faithfulness proxy, but it has a well-known limitation:
embedding similarity measures semantic and topical closeness, not logical consistency. An
answer can embed close to its source context while still contradicting it, inverting a number,
dropping a critical qualifier, or asserting something the context never states. Conversely, a
well-grounded answer that paraphrases heavily can score lower on similarity than its actual
faithfulness warrants. This gap between "about the same topic" and "actually entailed by the
source" is a recurring observation across the RAG-evaluation literature, and is the basic
motivation for a reasoning-capable judge — an LLM that reads context and answer together and
assesses entailment — rather than relying on similarity alone.

## Why Multiple Judges, Not One

Using an LLM to grade another LLM's output ("LLM-as-a-judge") is itself an established
technique, but a single judge model carries documented biases:

- **Verbosity bias** — rating longer, more elaborated answers as better independent of
  correctness.
- **Self-preference bias** — favoring outputs that resemble the judge's own style or model
  family.
- **Position bias** — in pairwise comparisons, favoring whichever answer is presented first.

These are widely discussed failure modes in the 2023–2026 LLM-evaluation literature. A
recognized mitigation is a panel of several judge models — often smaller or cheaper ones —
with their scores combined, rather than relying on a single large judge. This "jury" or
"panel of LLM evaluators" line of work (see the panel-of-judges prior art referenced in
[`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md#2026-landscape)) motivates RAGeval's
design: no single-judge fallback, at least two independently configured judge models scoring
every query, with both the consensus score and the judges' disagreement surfaced rather than
collapsed into an opaque number.

## What a Full Evaluation of That Design Found

Across every aggregation strategy tested against HaluEval-QA — an unweighted mean, an
accuracy-weighted mean, a precision-weighted mean with a variance penalty, a geometric median,
a disagreement-gated escalation cascade, a heterogeneous non-LLM panel member, and model
arbitration — consensus consistently falls short of the single strongest available judge
(Gemini 3.5 Flash on the primary benchmark) taken alone. Full numbers: [`BENCHMARK.md`](BENCHMARK.md).

This is the expected outcome of averaging when one judge is genuinely and consistently
stronger than the others. Averaging is a variance-reduction tool, not an accuracy-maximization
one: it helps when judges' errors are independent noise around a similar bias, and it hurts
when one judge is reliably better and the others are correlated in a weaker way — any point on
the line between a strong judge and weaker ones is, by construction, worse than the strong
judge alone. Weighting shifts that point closer to the strong judge without reaching it
(weighted consensus 0.838 versus Gemini alone 0.854 on the 240-example subset).

An escalation cascade — trusting the strongest judge by default and falling back to the full
panel only on signaled uncertainty, the pattern production LLM-as-judge pipelines typically
use — was tested as a more literature-aligned alternative to blending. Escalating on the
strongest judge's own proximity to the decision threshold rarely triggers, since this task's
per-judge scores are mostly confidently binary. Escalating on panel disagreement does trigger
on a real subset of cases, but measurably reduces accuracy: the strongest judge remains correct
on 78.6% of the cases where the other judges disagree with it, so blending in their comparatively
weaker verdicts moves more correct answers toward incorrect than it corrects genuine errors by
the strongest judge.

On this judge lineup and dataset, the quality gap between the strongest judge and the others is
large and consistent enough that no arithmetic combination of their scores — weighted,
variance-penalized, or cascade-gated — exceeds using the strongest judge alone. This matches
the literature's guidance for panels with a large quality spread (drop the weaker members, or
do not combine at all) rather than the guidance for panels of comparable-strength peers, where
averaging or majority vote helps. The panel's disagreement signal remains useful independently
of this: it correctly predicts where the blended score is more likely wrong, and is used as a
human-review escalation trigger rather than folded back into the score itself.

## Judge-Panel Literature and What Is Implemented From It

The finding above — a panel of same-genre LLM judges losing to its single strongest member —
is not unique to this dataset. Direct confirmation and two implementable responses to it are
now wired into `RAGEvaluator.score_groundedness_consensus()` as opt-in strategies.

- **["Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM Evaluation
  Panels"](https://arxiv.org/abs/2605.29800)** (Kohli, 2026) tested nine frontier judges across
  seven model families and found they carry only about two independent votes' worth of
  information, because they make the same mistakes on the same items. The paper's central
  claim — the best single judge matches or outperforms the full panel across all conditions
  tested, and smarter aggregation closes at most 11% of the gap even with ground truth
  available — matches this project's own measured result. The paper frames this as a
  correlated-judges problem rather than a combining-formula problem: no amount of arithmetic
  refinement over the same genre of judge escapes it.
- **[RoPoLL: Robust Panel of LLM Judges](https://arxiv.org/abs/2606.30931)** (Acharya et al.,
  Amazon, 2026) shows plain averaging has unbounded bias whenever even one judge fails in a
  correlated way, and proposes the geometric median as a tuning-free, breakdown-point-1/2
  robust replacement. For RAGeval's case — a scalar 0–1 score per judge, not a vector — the
  multivariate geometric median reduces to the classical weighted median, implemented as
  `RAGEvaluator._weighted_median()` and selectable via
  `RAGEVAL_AGGREGATION_STRATEGY=geometric_median`. Measured on the same 240-example subset, it
  does not close the gap to the single best judge, consistent with the correlated-judges
  explanation rather than a formula deficiency.
- **[Stopping and Routing LLM Judge Panels](https://arxiv.org/pdf/2608.19802)** (2026) frames a
  judge as a *copy* (adds no information), a *complement* (genuinely improves the panel), or a
  *specialist* (helps only on specific slices). On this dataset, the weaker judges behave as
  copies of the strongest one rather than complements.
- **["Beyond LLM-as-a-Judge: Independence-Aware Heterogeneous
  Evaluation"](https://zenodo.org/records/22368667)** argues that correlated errors arise
  because same-genre LLM judges share training data and failure modes, so the fix must change
  what is being combined, not just how. `RAGEvaluator.score_symbolic_groundedness()`
  implements this as a deterministic, non-LLM verification signal — numeric-fact consistency
  between the answer and retrieved context, plus lexical overlap — added as a structurally
  independent panel member, selectable via `RAGEVAL_INCLUDE_SYMBOLIC_JUDGE=true`. On the same
  240-example subset, the symbolic judge alone is weak (0.5625 accuracy — HaluEval-QA's
  hallucinations are predominantly invented facts and entities, not numeric errors), but
  folding it into the weighted-mean panel raises ROC-AUC from 0.8709 to 0.9191, a genuine
  improvement in ranking quality from an uncorrelated signal, though it does not move
  accuracy-at-threshold past the strongest judge alone.

Both strategies are opt-in rather than new defaults
(`RAGEVAL_AGGREGATION_STRATEGY=geometric_median`, `RAGEVAL_INCLUDE_SYMBOLIC_JUDGE=true`), since
enabling either changes an existing deployment's consensus number, which should be a
deliberate choice for a published package rather than a silent change on upgrade.

A fifth mechanism — a model arbitrating between judges' scores and rationales rather than a
fixed formula combining them — was evaluated directly (Groq and Gemini score independently, a
third model call sees both scores and rationales plus the original answer/context, and reaches
its own verdict, free to override either judge). Measured on HaluEval-QA, N=53: the arbiter
matches the single best judge exactly on accuracy and F1, and trails it on ROC-AUC. Full
numbers: [`BENCHMARK.md`](BENCHMARK.md#meta-judge--arbiter-panel-n53). This is the fifth
combination mechanism tested — following unweighted mean, weighted mean with a variance
penalty, geometric median, and a heterogeneous symbolic panel member — that does not exceed
the single strongest judge on this dataset. Consistency across five structurally different
mechanisms is itself evidence for the correlated-judges explanation: the ceiling reflects the
judges' shared correlation structure, not a deficiency in any particular way of combining them.

## Persona-Scoped Evaluation

Beyond groundedness and faithfulness, RAGeval flags when a persona-scoped answer surfaces
content from a business domain that persona should not have access to — for example, a
CFO-scoped assistant's answer citing headcount or HR figures. The underlying idea — checking
generated output against an authorization boundary — borrows from role-based access control
(RBAC), a decades-old access-control model (Ferraiolo & Kuhn, 1992), applied here to LLM
output rather than a data store.

None of the general-purpose RAG-evaluation frameworks cited below (RAGAS, ARES, TruLens) or the
observability platforms (Phoenix, Langfuse, DeepEval) ship a persona/role-scope axis alongside
groundedness, which makes this a genuinely distinctive feature of RAGeval rather than a
reimplementation of existing tooling. The implementation itself is a lightweight, explainable
heuristic — matching an answer's sentences against a per-domain term list
(`PERSONA_DOMAINS`/`DOMAIN_TERMS` in `evaluator.py`) — not a trained classifier, and RAGeval
does not yet publish a labeled dataset measuring that heuristic's own precision and recall as a
scope-violation detector. It should be treated as a useful, auditable signal for a first pass
at role-scope drift, not as a formally validated evaluation method in the way the
HaluEval-based groundedness numbers are.

## Where RAGeval Sits in the RAG-Evaluation Landscape

RAGeval is one of several tools built specifically to evaluate RAG pipelines rather than
general LLM output, and its design overlaps with, while differing in emphasis from, a few
established frameworks. RAGAS evaluates RAG systems along a triad of metrics — answer
relevance, faithfulness, and context precision/recall — computed largely via LLM-based scoring
against retrieved context and reference answers. ARES uses classifier models fine-tuned, often
with synthetic training data, to predict relevance and faithfulness judgments, positioning
itself as a lighter-weight alternative to calling a large LLM for every judgment. TruLens frames
its evaluation around a "RAG triad" — context relevance, groundedness, and answer relevance —
computed with configurable feedback functions, including LLM-based ones. RAGeval overlaps most
closely with the groundedness/faithfulness component of that landscape, but narrows its focus
to production observability — drop-in instrumentation, cost and latency tracking, a self-hosted
dashboard — and differentiates its scoring approach through multi-judge consensus rather than a
single configurable judge. It does not attempt to replicate RAGAS's or ARES's full metric
suites; a RAG pipeline evaluated in 2026 might use RAGeval for its observability and
consensus-groundedness angle alongside, rather than instead of, one of these frameworks for
other evaluation axes.

## Future Directions

- **Reporting the strongest judge as primary, with the panel as a review-escalation signal.**
  Five aggregation strategies tested against labeled data all underperform simply reporting the
  single strongest judge's score, with the panel's disagreement signal retained as a
  human-review trigger — already implemented — rather than a scoring input.
- **Calibration and stacking on held-out labels.** Weighting by raw accuracy, the current
  scheme, is a known-weak approach in the classifier-ensembling literature this generalizes
  from. Weighting by each judge's calibrated per-case confidence, or training a small stacking
  model on the judges' outputs against labeled data, is the better-supported alternative,
  currently untested for lack of a sufficiently large held-out label set.
- **A second, RAG-specific dataset.** HaluEval-QA is a general hallucination-detection
  benchmark, not one constructed specifically around retrieval-augmented generation. Adding
  RAGTruth (span-level hallucination annotation in RAG outputs) or a labeled sample of real
  production traffic would test whether the judge-strength ordering observed on HaluEval holds
  outside one dataset's particular construction of hallucinated answers.
- **Validating the persona-scope heuristic against labels.** The term-list flagging described
  above is a practical signal today; a labeled set of persona/answer pairs with human judgments
  of whether a scope violation occurred, precision/recall against that label set, and
  comparison against a learned classifier baseline would let it be reported with the same rigor
  as the groundedness numbers.

## Further Reading

- [`eval/JUDGE_BENCHMARK.md`](eval/JUDGE_BENCHMARK.md) — the HaluEval-based benchmark run, raw
  numbers, and their scope
- [`BENCHMARK.md`](BENCHMARK.md) — summary results across all tested consensus strategies
- [`README.md`](README.md) — feature overview and quick start
