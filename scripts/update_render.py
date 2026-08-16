import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

render_token = os.environ.get("RENDER_API_KEY")
url = "https://api.render.com/v1/services/srv-d9c0dt7aqgkc73dt6030/env-vars"
headers = {
    "Authorization": f"Bearer {render_token}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

data = [
    {"key": "GROQ_API_KEY", "value": os.environ.get("GROQ_API_KEY", "")},
    {"key": "ANTHROPIC_API_KEY", "value": os.environ.get("ANTHROPIC_API_KEY", "")},
    {"key": "GEMINI_API_KEY", "value": os.environ.get("GEMINI_API_KEY", "")},
    {"key": "OPENAI_API_KEY", "value": os.environ.get("OPENAI_API_KEY", "")},
    {"key": "JUDGE_MODELS", "value": "anthropic/claude-haiku-4-5,groq/llama-3.3-70b-versatile,gemini/gemini-flash-latest,openai/gpt-4o-mini"},
    {"key": "INFERENCE_MODE", "value": "remote"},
    {"key": "EMBEDDING_ENDPOINT", "value": "https://orchestrator-wf53.onrender.com/api/inference"},
    {"key": "INFERENCE_TOKEN", "value": os.environ.get("INFERENCE_TOKEN", "")},
    {"key": "OMNIINTEL_INTERNAL_TOKEN", "value": os.environ.get("OMNIINTEL_INTERNAL_TOKEN", "")},
    {"key": "REQUIRE_INTERNAL_TOKEN", "value": "true"},
    {"key": "RAGEVAL_POSTGRES_URL", "value": os.environ.get("RAGEVAL_POSTGRES_URL", "")},
    {"key": "POSTGRES_URL", "value": os.environ.get("POSTGRES_URL", "")},
    {"key": "RAGEVAL_STORE", "value": "postgres"},
    {"key": "ENVIRONMENT", "value": "production"},
    {"key": "CORS_ALLOWED_ORIGINS", "value": "*"}
]

res = requests.put(url, headers=headers, json=data)
print(res.status_code)
print(res.text)

# Also force a deployment
deploy_url = "https://api.render.com/v1/services/srv-d9c0dt7aqgkc73dt6030/deploys"
res = requests.post(deploy_url, headers=headers, json={"clearCache": "do_not_clear"})
print("Deploy response:")
print(res.status_code)
print(res.text)
