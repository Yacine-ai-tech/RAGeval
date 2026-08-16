import requests
import json
import random
import os

prod_url = "https://rageval-4xh5.onrender.com"
token = "***REMOVED-SECRET***"
docs_dir = "/home/ai-sniper/Downloads/credential/global_docs"

headers = {
    "Content-Type": "application/json",
    "X-OmniIntel-Internal-Token": token
}

def load_large_docs():
    # Read all markdown files in global_docs to create a massive corpus
    corpus = []
    print(f"Reading docs from {docs_dir}...")
    for filename in os.listdir(docs_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                # Split into chunks of ~2000 chars for context
                for i in range(0, len(content), 2000):
                    chunk = content[i:i+2000]
                    if len(chunk) > 500:
                        corpus.append(chunk)
    
    print(f"Loaded {len(corpus)} large chunks from global_docs.")
    
    # Generate some mock evaluation requests using the large contexts
    queries = [
        "How do you handle API fallback?",
        "What is the deployment strategy?",
        "How is authentication handled in the services?",
        "Explain the pricing model.",
        "How do we handle rate limits?",
        "What is the vector search database?",
        "Detail the security protocols."
    ]
    
    samples_to_test = 5
    print(f"Sending {samples_to_test} requests with massive context arrays to Prod...")
    
    for i in range(samples_to_test):
        q = random.choice(queries)
        # Select 3 random large chunks as the context (retrieved context)
        selected_chunks = random.sample(corpus, min(3, len(corpus)))
        
        # We will use the chunks themselves as the answer to simulate a summarization
        answer = selected_chunks[0][:500] + "..."
        
        payload = {
            "query": q,
            "answer": answer,
            "chunks": selected_chunks,
            "tokens_used": sum(len(c.split()) for c in selected_chunks) + len(answer.split()),
            "latency_ms": random.uniform(800, 2500),
            "model": "gpt-4o",
            "persona": "Documentation Bot",
            "session_id": "test-large-docs-session" # Explicit session to test isolation
        }
        
        context_size = sum(len(c) for c in selected_chunks)
        print(f"\n[{i+1}/{samples_to_test}] Query: {q}")
        print(f"Context payload size: {context_size} chars across {len(selected_chunks)} large chunks.")
        
        try:
            res = requests.post(f"{prod_url}/eval/log", json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                scores = res.json()
                print(f"✅ Success! Relevance: {scores.get('relevance')}, Groundedness: {scores.get('groundedness')}")
                print(f"Consensus Judges Used: {scores.get('groundedness_consensus', {}).get('judges_used')}")
            else:
                print(f"❌ Failed: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    load_large_docs()
