import requests
import json
import asyncio
import websockets

prod_url = "https://rageval-4xh5.onrender.com"
ws_url = "wss://rageval-4xh5.onrender.com"
token = "omniintel-prod-internal-2026"

headers = {
    "Content-Type": "application/json",
    "X-OmniIntel-Internal-Token": token
}

def print_res(name, res):
    print(f"--- {name} ---")
    print("Status:", res.status_code)
    try:
        print(json.dumps(res.json(), indent=2)[:500] + ("..." if len(res.text) > 500 else ""))
    except:
        print(res.text[:500])
    print()

def test_endpoints():
    print("Starting Comprehensive Prod Test...\n")
    
    # 1. /health
    res = requests.get(f"{prod_url}/health", headers=headers, timeout=60)
    print_res("GET /health", res)

    # 2. /eval/config
    res = requests.get(f"{prod_url}/eval/config", headers=headers, timeout=60)
    print_res("GET /eval/config", res)

    # 3. /eval/log
    log_payload = {
        "query": "Who is the CEO?",
        "answer": "Yacine is the CEO.",
        "chunks": ["Yacine founded the company and is the CEO."],
        "tokens_used": 150,
        "latency_ms": 1200,
        "model": "gpt-4o-mini"
    }
    res = requests.post(f"{prod_url}/eval/log", json=log_payload, headers=headers, timeout=60)
    print_res("POST /eval/log", res)

    # 4. /eval/metrics
    res = requests.get(f"{prod_url}/eval/metrics?days=7", headers=headers, timeout=60)
    print_res("GET /eval/metrics", res)

    # 5. /eval/queries
    res = requests.get(f"{prod_url}/eval/queries?limit=5", headers=headers, timeout=60)
    print_res("GET /eval/queries", res)

    # 6. /eval/cost-report
    res = requests.get(f"{prod_url}/eval/cost-report", headers=headers, timeout=60)
    print_res("GET /eval/cost-report", res)

    # 7. /eval/alerts
    res = requests.get(f"{prod_url}/eval/alerts", headers=headers, timeout=60)
    print_res("GET /eval/alerts", res)

    # 8. /eval/retrieval-bench
    bench_payload = {
        "queries": ["What is revenue?"],
        "chunks_a": [["Revenue is 5M"]],
        "chunks_b": [["Revenue was 5M in Q1"]]
    }
    res = requests.post(f"{prod_url}/eval/retrieval-bench", json=bench_payload, headers=headers, timeout=60)
    print_res("POST /eval/retrieval-bench", res)
    
    # 9. /eval/embedding-comparison
    embed_payload = {
        "queries": ["What is revenue?"],
        "chunks": [["Revenue is 5M"]]
    }
    res = requests.post(f"{prod_url}/eval/embedding-comparison", json=embed_payload, headers=headers, timeout=60)
    print_res("POST /eval/embedding-comparison", res)

    # 10. Test UI Pages on Vercel
    ui_url = "https://rageval-ui-2026.vercel.app"
    pages = ["/", "/traces", "/benchmarks", "/costs"]
    print("--- UI Pages ---")
    for p in pages:
        res = requests.get(f"{ui_url}{p}", timeout=60)
        print(f"GET {p}: {res.status_code}")
    print()

async def test_websocket():
    print("--- WS /eval/live ---")
    try:
        async with websockets.connect(f"{ws_url}/eval/live") as ws:
            # Wait for at most 3 seconds for messages
            messages = []
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    messages.append(msg)
                except asyncio.TimeoutError:
                    break
            print(f"Received {len(messages)} events via websocket.")
            if messages:
                print("Latest event:", messages[0][:200])
    except Exception as e:
        print("WS Error:", str(e))

if __name__ == "__main__":
    test_endpoints()
    asyncio.run(test_websocket())
