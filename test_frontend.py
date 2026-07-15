import requests

payload = {
    "query": "What was Q3 revenue and how did gross margin move?",
    "answer": "Q3 revenue was $487.6M, up 18.7% year over year. Gross margin expanded to 46.8% from 43.1% in Q2, driven by improved product mix and lower logistics costs.",
    "chunks": [
        "Q3 FY2025 revenue: $487.6M (+12.4% QoQ, +18.7% YoY).",
        "Gross margin Q3: 46.8% vs 43.1% in Q2; drivers: product mix, pricing discipline, logistics costs.",
        "Operating costs were flat at $93.2M (+1.2% QoQ)."
    ],
    "persona": "cfo",
    "model": "manual/evaluate-page"
}

try:
    from fastapi.testclient import TestClient
    from api import app
    client = TestClient(app)
    response = client.post("/eval/score", json=payload)
    print(response.json())
except Exception as e:
    import logging; logging.error(f'Error: {e}', exc_info=True)
    print(e)
