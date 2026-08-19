"""Manual live smoke test for the Gemini judge path in RAGEvaluator._judge_groundedness().

Exercises the real evaluator code (not a hand-rolled copy of the genai call) so this
script can't silently drift out of sync with the actual thinking_config / fallback
logic. Pass a model name to test something other than the default judge model, e.g.:

    python scripts/test_gemini_judge.py gemini/gemini-flash-lite-latest
"""
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


async def test(model: str):
    from rageval.evaluator import RAGEvaluator

    ev = RAGEvaluator()
    answer = "Acme's Q2 revenue was $4.2M, a 20% year-over-year increase."
    context = "Acme Corp Q2 revenue was $4.2M, up 20% year over year."

    print(f"Testing {model}...")
    score = await ev._judge_groundedness(answer, context, model=model)
    if score is None:
        print("FAILED: judge returned None (see WARNING log above for the reason)")
    else:
        print(f"Success: score={score}")


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "gemini/gemini-flash-latest"
    asyncio.run(test(model))
