import requests
import json
import random

prod_url = "https://rageval-4xh5.onrender.com"
token = "***REMOVED-SECRET***"

headers = {
    "Content-Type": "application/json",
    "X-OmniIntel-Internal-Token": token
}

def test_matching_data():
    scenarios = [
        # Scenario 1: Standard factual question (High Relevance, High Groundedness)
        {
            "query": "What is the vector search database?",
            "answer": "The system uses pgvector on Neon PostgreSQL for vector search.",
            "chunks": [
                "Our application utilizes Neon PostgreSQL with the pgvector extension to perform efficient vector search and storage for our embeddings."
            ]
        },
        # Scenario 2: Multi-turn complex question
        {
            "query": "User: Can you explain the pricing?\nSystem: The API is $5 per month.\nUser: What if I go over the limit?",
            "answer": "If you exceed the API limit, you will be charged $0.01 per additional request.",
            "chunks": [
                "Pricing is a flat rate of $5 per month for the base tier. If you exceed the usage limit, you are charged $0.01 per additional request."
            ]
        },
        # Scenario 3: Persona Scope verification (Testing domain boundary correctly respected)
        {
            "query": "What is the employee attrition rate?",
            "answer": "I am the CFO, so I cannot speak to employee attrition. You would need to check with the CHRO for People metrics.",
            "chunks": [
                "Employee attrition rate stands at 5% this quarter."
            ],
            "persona": "cfo"
        }
    ]
    
    print(f"Sending {len(scenarios)} matching real-data requests to Prod...\n")
    
    for i, data in enumerate(scenarios):
        payload = {
            "query": data["query"],
            "answer": data["answer"],
            "chunks": data["chunks"],
            "tokens_used": 120,
            "latency_ms": 1100,
            "model": "gpt-4o",
            "persona": data.get("persona"),
            "session_id": "test-matching-data-session"
        }
        
        print(f"[{i+1}/{len(scenarios)}] Query: {data['query'][:50]}...")
        
        try:
            res = requests.post(f"{prod_url}/eval/log", json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                scores = res.json()
                print(f"✅ Success!")
                print(f"   Relevance: {scores.get('relevance'):.4f}")
                print(f"   Groundedness: {scores.get('groundedness'):.4f}")
                print(f"   Faithfulness: {scores.get('faithfulness'):.4f}")
                if scores.get("persona_scope_violations"):
                    print(f"   ⚠️ Persona Scope Violations: {scores['persona_scope_violations']}")
                print(f"   Consensus Judges Used: {scores.get('groundedness_consensus', {}).get('judges_used')}")
            else:
                print(f"❌ Failed: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("-" * 50)

if __name__ == "__main__":
    test_matching_data()
