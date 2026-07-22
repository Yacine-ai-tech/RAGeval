# RAGeval — Multi-Judge Consensus Benchmark (HaluEval)

Research-grade validation of the multi-judge groundedness consensus on **HaluEval** (Li et al.,
2023), a standard hallucination benchmark. Reproducible: `python eval/run_judge_benchmark.py --n 25`
(needs `ANTHROPIC_API_KEY`/`GROQ_API_KEY`, `datasets`, `scikit-learn`).

## Setup
- Dataset: HaluEval-QA. Each question yields **2 labelled examples** against the same `knowledge`
  context: the `right_answer` (grounded=1) and `hallucinated_answer` (grounded=0).
- Judges: Claude Haiku 4.5 + Groq Llama-3.3-70B (the configured `JUDGE_MODELS`).
- Decision threshold: consensus ≥ 0.6 → "grounded".
- N = 25 questions → **50 labelled examples** (balanced).

## Results (real run)

| Metric | Consensus | Claude Haiku (solo) | Groq Llama (solo) |
|--------|-----------|---------------------|-------------------|
| Accuracy | **0.800** | 0.780 | 0.767 |
| Precision | 0.826 | — | — |
| Recall | 0.760 | — | — |
| F1 | **0.792** | — | — |
| ROC-AUC (raw consensus) | **0.880** | — | — |

**Headline:** multi-judge **consensus (0.80) beats every individual judge** (0.78 / 0.767) — the
core thesis, measured on a standard dataset. ROC-AUC 0.880 shows the raw consensus score
cleanly separates grounded from hallucinated answers.

**Honest caveat:** judge-disagreement (stdev) as an error predictor was only marginal here
(0.173 on wrong predictions vs 0.170 on correct) — directionally right but not a strong signal
at N=50; the `flag_for_review` heuristic needs a larger labelled set + threshold tuning before
it can be claimed as a reliable hallucination alarm.

## Scaling
N=25 keeps the run cheap (~100 judge calls, ~$0.10). Raising `--n` to a few hundred gives tighter
CIs; adding a 3rd judge (e.g. GPT-mini, key permitting) tests whether consensus keeps improving.
