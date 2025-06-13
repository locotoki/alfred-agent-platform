#!/usr/bin/env python3
"""Agent-core Performance Test Harness Scaffold.

Target: 10 RPS for 60s, p95 < 300ms, error rate < 1%
"""

import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Configuration
BASE_URL = os.getenv("TARGET_URL", "http://localhost:8080")
TARGET_RPS = int(os.getenv("QPS", "10"))
DURATION_SECONDS = int(os.getenv("DURATION", "60"))
MAX_WORKERS = 20

# Sample queries (≈150 chars each)
SAMPLE_QUERIES = [
    "What is the EmbeddingRepo interface and how does it handle vector similarity search?",
    "How does the agent-core MVP implement retrieval-augmented generation with citations?",
    "What are the key metrics exported by the retrieval endpoint for observability?",
    "Explain the vector schema design for the documents table in PostgreSQL.",
    "How does the platform ensure p95 latency stays under 300ms at 10 QPS load?",
]

def make_request(query_text):
    """Make a single request to the retrieval endpoint."""
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/v1/query",
            json={"query": query_text, "top_k": 8},
            timeout=5,  # Client-side timeout
        )
        latency_ms = (time.time() - start_time) * 1000
        return {
            "success": response.status_code == 200,
            "latency_ms": latency_ms,
            "status_code": response.status_code,
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {"success": False, "latency_ms": latency_ms, "error": str(e)}

def run_load_test():
    """Run the performance test."""
    print("🚀 Starting performance test: {} RPS for {}s".format(TARGET_RPS, DURATION_SECONDS))
    print("Target: p95 < 300ms, error rate < 1%\n")

    results = []
    start_time = time.time()
    request_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []

        while time.time() - start_time < DURATION_SECONDS:
            # Submit requests to maintain target RPS
            query = SAMPLE_QUERIES[request_count % len(SAMPLE_QUERIES)]
            future = executor.submit(make_request, query)
            futures.append(future)
            request_count += 1

            # Sleep to maintain target RPS
            time.sleep(1.0 / TARGET_RPS)

        # Collect results
        print(f"⏳ Waiting for {len(futures)} requests to complete...")
        for future in as_completed(futures):
            results.append(future.result())

    # Calculate metrics
    successful_requests = [r for r in results if r["success"]]
    latencies = [r["latency_ms"] for r in successful_requests]

    if latencies:
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile
        error_rate = (len(results) - len(successful_requests)) / len(results) * 100

        print("\n📊 Performance Test Results")
        print("=" * 40)
        print(f"Total requests: {len(results)}")
        print(f"Successful: {len(successful_requests)}")
        print(f"Error rate: {error_rate:.2f}%")
        print("\nLatency percentiles:")
        print(f"  p50: {p50:.2f}ms")
        print(f"  p95: {p95:.2f}ms {'✅' if p95 < 300 else '❌'}")
        print(f"  p99: {p99:.2f}ms")
        print(f"\n{'✅ PASS' if p95 < 300 and error_rate < 1 else '❌ FAIL'}")
    else:
        print("❌ No successful requests - check if server is running")

if __name__ == "__main__":
    # Quick health check first
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=2)
        if health.status_code == 200:
            print("✅ Health check passed\n")
            run_load_test()  # type: ignore
        else:
            print(f"❌ Health check failed: {health.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print(f"Make sure the server is running on {BASE_URL}")
