import requests
import json

prod_url = "https://rageval-4xh5.onrender.com"
token = "omniintel-prod-internal-2026"

headers = {
    "Content-Type": "application/json",
    "X-OmniIntel-Internal-Token": token
}

def test_all_flags():
    scenarios = [
        # 1. JUDGE_DISAGREEMENT
        # A tricky edge case: Implicit deduction / math logic. Some judges accept the math as grounded, others strictly reject it because the exact number isn't in the text.
        {
            "name": "Trigger: JUDGE_DISAGREEMENT",
            "query": "Is Python supported by the application?",
            "answer": "Yes, Python is fully supported.",
            "chunks": [
                "It is completely false to assert that the application fails to not reject Python deployments."
            ],
            "persona": "system"
        },
        # 2. POTENTIAL_HALLUCINATION & HIGH_LATENCY
        # The answer is a blatant hallucination contradicting the context, and it took 6 seconds to generate.
        {
            "name": "Trigger: POTENTIAL_HALLUCINATION & HIGH_LATENCY",
            "query": "What languages do we support?",
            "answer": "We exclusively support Rust and Go. Python is strictly prohibited.",
            "chunks": [
                "The core application is built entirely in Python, utilizing FastAPI and Pydantic for robust type validation."
            ],
            "latency_ms": 6500, # > 5000 triggers HIGH_LATENCY
            "persona": "engineer"
        },
        # 3. LOW_RETRIEVAL_RELEVANCE
        # The retrieved context has absolutely nothing to do with the user's query.
        {
            "name": "Trigger: LOW_RETRIEVAL_RELEVANCE",
            "query": "How do I configure the database connection?",
            "answer": "You configure the database using the POSTGRES_URL environment variable.",
            "chunks": [
                "The corporate holiday schedule includes December 25th, January 1st, and Thanksgiving Day. Paid time off must be requested 2 weeks in advance."
            ],
            "persona": "system"
        },
        # 4. PERSONA_SCOPE_VIOLATION
        # The CFO persona surfaces a People/HR metric (headcount/attrition) which violates its RBAC domain.
        {
            "name": "Trigger: PERSONA_SCOPE_VIOLATION",
            "query": "Can you give me a company update?",
            "answer": "Revenue is up 20% this year. We also saw a significant headcount reduction, with employee attrition hitting 12%.",
            "chunks": [
                "Q3 Financials: Revenue up 20%. HR Report: Headcount reduction executed smoothly, employee attrition at 12%."
            ],
            "persona": "cfo" # CFO is mapped to 'finance', but answer includes 'headcount' and 'attrition' (people domain)
        }
    ]
    
    print(f"Sending {len(scenarios)} Edge-Case Edge-Case requests to trigger RAGeval Flags...\n")
    
    for i, data in enumerate(scenarios):
        payload = {
            "query": data["query"],
            "answer": data["answer"],
            "chunks": data["chunks"],
            "tokens_used": 150,
            "latency_ms": data.get("latency_ms", 1200),
            "model": "gpt-4o",
            "persona": data.get("persona"),
            "session_id": "test-flags-session"
        }
        
        print(f"--- Scenario {i+1}: {data['name']} ---")
        
        try:
            res = requests.post(f"{prod_url}/eval/log", json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                scores = res.json()
                print(f"   Relevance: {scores.get('relevance'):.4f}")
                print(f"   Groundedness: {scores.get('groundedness'):.4f}")
                print(f"   🚩 FLAGS TRIGGERED: {scores.get('flags')}")
                if "groundedness_consensus" in scores:
                    judges = scores["groundedness_consensus"].get("judges", [])
                    print("   Individual Judge Votes:")
                    for j in judges:
                        print(f"      - {j['model']}: {j['score']}")
            else:
                print(f"❌ Failed: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("\n")

if __name__ == "__main__":
    test_all_flags()
