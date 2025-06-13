"""Benchmark tests for ML inference performance."""

import numpy as np
import pytest
from sentence_transformers import SentenceTransformer

@pytest.fixture(scope="module")
def model():
    """Shared model for inference tests."""
    return SentenceTransformer("all-MiniLM-L6-v2")

@pytest.mark.benchmark
def test_single_inference_latency(benchmark, model):
    """Benchmark single alert inference latency."""
    test_alert = "API timeout error in service X"

    benchmark(model.encode, test_alert)

    # P99 latency must be < 15ms
    assert benchmark.stats["max"] < 0.015  # 15ms

@pytest.mark.benchmark
def test_batch_inference_throughput(benchmark, model):
    """Benchmark batch inference throughput."""
    # Create batch of alerts
    batch_size = 32
    test_alerts = [f"Alert {i}: Service error detected" for i in range(batch_size)]

    def process_batch():
        embeddings = model.encode(test_alerts)
        return embeddings

    benchmark(process_batch)

    # Should process 32 alerts in < 200ms
    assert benchmark.stats["mean"] < 0.2

@pytest.mark.benchmark
def test_large_batch_performance(benchmark, model):
    """Test performance with large batches."""
    batch_size = 1000
    test_alerts = [f"Alert {i}: Random error {np.random.rand()}" for i in range(batch_size)]

    def process_large_batch():
        # Process in smaller chunks to avoid memory issues
        chunk_size = 100
        all_embeddings = []

        for i in range(0, len(test_alerts), chunk_size):
            chunk = test_alerts[i : i + chunk_size]
            embeddings = model.encode(chunk)
            all_embeddings.append(embeddings)

        return np.vstack(all_embeddings)

    benchmark(process_large_batch)

    # Should process 1000 alerts in < 5 seconds
    assert benchmark.stats["mean"] < 5.0

@pytest.mark.benchmark
def test_memory_efficiency():
    """Test inference memory usage."""
    import psutil
    process = psutil.Process()

    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Measure memory before
    initial_memory = process.memory_info().rss / 1e6  # MB

    # Process many alerts
    for _ in range(10):
        alerts = [f"Alert {i}" for i in range(100)]
        model.encode(alerts)

    # Measure memory after
    final_memory = process.memory_info().rss / 1e6  # MB
    memory_increase = final_memory - initial_memory

    # Memory increase should be minimal (< 100MB)
    assert memory_increase < 100, f"Memory increased by {memory_increase}MB"
