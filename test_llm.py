import litellm
import asyncio
import os

async def main():
    litellm.drop_params = True
    for model in ["groq/llama-3.3-70b-versatile", "anthropic/claude-haiku-4-5"]:
        try:
            resp = await litellm.acompletion(
                model=model,
                messages=[{
                    "role": "user",
                    "content": "Is this answer fully supported by the context? Score 0.0-1.0 (0=hallucinated, 1=fully grounded). Return ONLY the float number, nothing else.\n\nAnswer: The capital of France is Paris.\n\nContext: Paris is the capital and most populous city of France."
                }],
                temperature=0.0,
            )
            print(f"{model} returned: {resp.choices[0].message.content}")
        except Exception as e:
            print(f"{model} error: {e}")

asyncio.run(main())
