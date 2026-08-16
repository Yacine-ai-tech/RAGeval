import requests
import json

prod_url = "https://rageval-4xh5.onrender.com"
token = "omniintel-prod-internal-2026"

def test_score():
    print("Testing /eval/score on PROD...")
    payload = {
        "query": "What is the Q3 margin?",
        "chunks": ["Margin is 18.5%."],
        "answer": "18.5%"
    }
    headers = {
        "Content-Type": "application/json",
        "X-OmniIntel-Internal-Token": token
    }
    resp = requests.post(f"{prod_url}/eval/score", json=payload, headers=headers)
    print("Status:", resp.status_code)
    try:
        data = resp.json()
        print("Response:", json.dumps(data, indent=2))
        
        consensus = data.get("groundedness_consensus", {})
        print("Judges used:", len(consensus.get("judges", [])))
        print("Judges:", consensus.get("judges"))
        
    except Exception as e:
        print("Failed to parse JSON:", resp.text)

if __name__ == "__main__":
    test_score()
