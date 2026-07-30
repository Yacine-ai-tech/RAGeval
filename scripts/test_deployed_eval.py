#!/usr/bin/env python3
"""
Test RAGeval deployed service with real data evaluation
Tests the health, evaluation, and benchmark endpoints
"""
import httpx
import json

# Deployed service URL
RAGEVAL_URL = "https://rageval.ysiddo-ai-projects.app"

def test_health():
    """Test health endpoint"""
    print("Testing RAGeval Health...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{RAGEVAL_URL}/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Health Check: {result.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Health Check Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        return False

def test_evaluation():
    """Test evaluation endpoint with sample data"""
    print("\nTesting RAG Evaluation...")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            # Sample RAG evaluation data
            eval_data = {
                "query": "What is the capital of France?",
                "contexts": ["France is a country in Europe. Paris is its capital city."],
                "answer": "The capital of France is Paris.",
                "tokens_used": 50,
                "latency_ms": 125.5,
                "model": "groq/llama-3.3-70b-versatile"
            }
            
            response = client.post(f"{RAGEVAL_URL}/eval/score", json=eval_data)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ RAG Evaluation: {result}")
                return True
            else:
                print(f"❌ RAG Evaluation Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ RAG Evaluation Error: {e}")
        return False

def test_benchmark():
    """Test retrieval benchmark endpoint"""
    print("\nTesting Retrieval Benchmark...")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            # Sample benchmark data
            benchmark_data = {
                "queries": ["What is the capital of France?", "What is 2+2?"],
                "chunks_a": [
                    ["France is a country in Europe. Paris is its capital city."],
                    ["Basic arithmetic: 2+2 equals 4."]
                ],
                "chunks_b": [
                    ["Paris is the capital city of France."],
                    ["2+2 = 4"]
                ]
            }
            
            response = client.post(f"{RAGEVAL_URL}/eval/retrieval-bench", json=benchmark_data)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Retrieval Benchmark: {result}")
                return True
            else:
                print(f"❌ Retrieval Benchmark Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Retrieval Benchmark Error: {e}")
        return False

def test_metrics():
    """Test metrics endpoint"""
    print("\nTesting Metrics...")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{RAGEVAL_URL}/eval/metrics?days=7")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Metrics: {result}")
                return True
            else:
                print(f"❌ Metrics Failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Metrics Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("RAGeval Testing Against Deployed Service")
    print("=" * 60)
    
    results = {
        "Health Check": test_health(),
        "RAG Evaluation": test_evaluation(),
        "Benchmark": test_benchmark(),
        "Metrics": test_metrics()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print("=" * 60)