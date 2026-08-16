import os
import asyncio

from dotenv import load_dotenv
load_dotenv()

async def test():
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(http_options={"api_version": "v1beta"})
        
        prompt = "Is this answer fully supported by the context? Score 0.0-1.0. Answer: yes. Context: yes."
        print("Testing gemini-flash-latest...")
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-flash-latest",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        print("Success:", resp.text)
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test())
