from rageval.evaluator import RAGEvaluator
import asyncio

async def main():
    ev = RAGEvaluator()
    res = await ev.score_interaction(
        query="What is the capital of France?",
        answer="The capital of France is Paris.",
        chunks=["Paris is the capital and most populous city of France."],
        tokens_used=10,
        latency_ms=100.0,
        model="groq/llama-3.3-70b-versatile"
    )
    print(res)

asyncio.run(main())
