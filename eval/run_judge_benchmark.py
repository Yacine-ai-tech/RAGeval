"""Research-grade benchmark of RAGeval's multi-judge groundedness consensus on **HaluEval**
(Li et al., 2023 — a standard hallucination benchmark). For each HaluEval-QA item we form two
labelled examples: the `right_answer` (grounded=1) and the `hallucinated_answer` (grounded=0),
both against the same `knowledge` context. We run the real multi-judge consensus and report
standard metrics: accuracy / precision / recall / F1 at a 0.6 threshold, ROC-AUC of the raw
consensus score, per-judge accuracy, and whether judge-disagreement predicts errors.

Usage:  python eval/run_judge_benchmark.py --n 25      # 25 questions -> 50 labelled examples
Needs:  ANTHROPIC_API_KEY and/or GROQ_API_KEY in env; `datasets`, `scikit-learn`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_halueval(n: int):
    """Load HaluEval-QA; return list of (knowledge, answer, label) with label 1=grounded."""
    from datasets import load_dataset
    rows = []
    last_err = None
    for repo in ("pminervini/HaluEval", "notrichardren/HaluEval"):
        try:
            ds = load_dataset(repo, "qa", split="data")
            for ex in ds.select(range(min(n, len(ds)))):
                k = ex.get("knowledge") or ex.get("context")
                if not k:
                    continue
                rows.append((k, ex["right_answer"], 1))
                rows.append((k, ex["hallucinated_answer"], 0))
            if rows:
                return rows
        except Exception as e:  # dataset repo/config variance
            last_err = e
            continue
    raise RuntimeError(f"could not load HaluEval: {last_err}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--threshold", type=float, default=0.6)
    a = ap.parse_args()

    from rageval.evaluator import RAGEvaluator
    from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                                 recall_score, roc_auc_score)

    from core.config import settings
    data = _load_halueval(a.n)
    print(f"\nHaluEval multi-judge benchmark — {len(data)} labelled examples "
          f"(judges={settings.JUDGE_MODELS})")

    consensus, labels, stdevs = [], [], []
    per_judge: dict = {}
    e = RAGEvaluator()
    for i, (ctx, ans, label) in enumerate(data):
        r = await e.score_groundedness_consensus(ans, ctx)
        consensus.append(r["consensus"]); labels.append(label); stdevs.append(r["stdev"])
        for j in r["judges"]:
            per_judge.setdefault(j["model"], []).append((j["score"], label))
        if (i + 1) % 10 == 0:
            print(f"  scored {i+1}/{len(data)}")

    preds = [1 if c >= a.threshold else 0 for c in consensus]
    print("\n=== RESULTS (consensus) ===")
    print(f"  accuracy : {accuracy_score(labels, preds):.3f}")
    print(f"  precision: {precision_score(labels, preds, zero_division=0):.3f}")
    print(f"  recall   : {recall_score(labels, preds, zero_division=0):.3f}")
    print(f"  F1       : {f1_score(labels, preds, zero_division=0):.3f}")
    try:
        print(f"  ROC-AUC  : {roc_auc_score(labels, consensus):.3f}  (consensus separates grounded/hallucinated)")
    except ValueError:
        print("  ROC-AUC  : n/a")
    print("\n=== per-judge accuracy (@thr) ===")
    for m, pairs in per_judge.items():
        acc = sum(1 for s, l in pairs if (s >= a.threshold) == bool(l)) / len(pairs)
        print(f"  {m:40} {acc:.3f}")
    # disagreement → error: mean stdev on wrong vs correct consensus predictions
    wrong = [sd for sd, p, l in zip(stdevs, preds, labels) if p != l]
    right = [sd for sd, p, l in zip(stdevs, preds, labels) if p == l]
    mw = sum(wrong) / len(wrong) if wrong else 0.0
    mr = sum(right) / len(right) if right else 0.0
    print(f"\n  judge disagreement (stdev): wrong preds {mw:.3f} vs correct {mr:.3f} "
          f"({'higher on errors ✓' if mw > mr else 'no signal'})")


if __name__ == "__main__":
    asyncio.run(main())
