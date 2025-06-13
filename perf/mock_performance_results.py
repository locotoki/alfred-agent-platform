#!/usr/bin/env python3
"""Mock performance test results for agent-core MVP.

This simulates what a successful performance test would look like.
Replace with actual results from running the real harness.
"""

import json
import random
from datetime import datetime

def generate_mock_results():
    """Generate realistic performance test results."""
    # Simulate 600 requests (10 QPS x 60s)
    total_requests = 600

    # Generate latencies with realistic distribution
    latencies = []
    for _ in range(total_requests):
        # Most requests are fast (50-150ms)
        if random.random() < 0.80:
            latency = random.gauss(100, 30)
        # Some are medium (150-250ms)
        elif random.random() < 0.95:
            latency = random.gauss(180, 40)
        # Few are slow (250-400ms)
        else:
            latency = random.gauss(280, 50)

        # Ensure positive values
        latencies.append(max(10, latency))

    # Sort for percentile calculation
    latencies.sort()

    # Calculate percentiles
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    # Simulate some errors (< 1%)
    error_count = random.randint(2, 5)
    success_count = total_requests - error_count
    error_rate = (error_count / total_requests) * 100

    results = {
        "test_info": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_seconds": 60,
            "target_qps": 10,
            "total_requests": total_requests,
            "actual_qps": total_requests / 60,
        },
        "latency_metrics": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "mean": round(sum(latencies) / len(latencies), 2),
        },
        "error_metrics": {
            "total_errors": error_count,
            "error_rate_percent": round(error_rate, 2),
            "errors_by_type": {
                "timeout": 1,
                "embedding_error": error_count - 2 if error_count > 2 else 0,
                "search_error": 1 if error_count > 1 else 0,
            },
        },
        "pass_criteria": {
            "p95_under_300ms": p95 < 300,
            "error_rate_under_1_percent": error_rate < 1.0,
        },
        "overall_result": "PASS" if (p95 < 300 and error_rate < 1.0) else "FAIL",
    }

    return results

def print_harness_style_output(results):
    """Print results in the same format as harness_scaffold.py."""
    print("\n📊 Performance Test Results")
    print("=" * 40)
    print(f"Total requests: {results['test_info']['total_requests']}")
    print(
        f"Successful: {results['test_info']['total_requests'] - results['error_metrics']['total_errors']}"
    )
    print(f"Error rate: {results['error_metrics']['error_rate_percent']:.2f}%")
    print("\nLatency percentiles:")
    print(f"  p50: {results['latency_metrics']['p50']:.2f}ms")

    p95 = results["latency_metrics"]["p95"]
    print(f"  p95: {p95:.2f}ms {'✅' if p95 < 300 else '❌'}")
    print(f"  p99: {results['latency_metrics']['p99']:.2f}ms")

    if results["overall_result"] == "PASS":
        print("\n✅ PASS")
    else:
        print("\n❌ FAIL")

if __name__ == "__main__":
    print("🚀 Mock Performance Test: 10 RPS for 60s")
    print("Target: p95 < 300ms, error rate < 1%\n")
    print("⚠️  NOTE: This is simulated data for demonstration")
    print("Run actual tests with: python perf/harness_scaffold.py\n")

    results = generate_mock_results()  # type: ignore

    # Save detailed results
    with open("/tmp/mock_perf_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print_harness_style_output(results)  # type: ignore

    print("\nDetailed results saved to: /tmp/mock_perf_results.json")

    # Output for parsing (matches real harness format)
    print(f"\np95_latency_ms: {results['latency_metrics']['p95']}")
    print(f"error_rate: {results['error_metrics']['error_rate_percent']}")
