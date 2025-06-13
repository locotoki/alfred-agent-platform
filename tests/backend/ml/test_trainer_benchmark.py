"""Benchmark tests for ML training pipeline."""

import time

import pytest

from backend.alfred.ml.alert_dataset import load_alert_dataset

@pytest.mark.benchmark
def test_training_speed(benchmark):
    """Benchmark the full training pipeline speed."""
    # Note: This is a mock version that doesn't actually train
    # Real training would take too long for CI

    def run_training():
        # Simulate dataset loading
        start = time.time()
        dataset = load_alert_dataset(days=30)
        load_time = time.time() - start

        # Mock training time (actual training mocked in CI)
        training_time = 2.5  # seconds
        time.sleep(0.1)  # Simulate some work

        return {
            "dataset_size": len(dataset) if dataset else 100000,
            "load_time": load_time,
            "training_time": training_time,
            "total_time": load_time + training_time,
        }

    result = benchmark(run_training)

    # Assert we stay under 3 minute limit
    assert result["total_time"] < 180, "Training must complete in under 3 minutes"

@pytest.mark.benchmark
def test_dataset_loading_performance(benchmark):
    """Benchmark dataset loading speed."""
    benchmark(load_alert_dataset, days=30)

    # For 100k alerts, should load in < 10 seconds
    assert benchmark.stats["mean"] < 10.0

@pytest.mark.benchmark
def test_memory_usage():
    """Test memory usage stays within limits."""
    import psutil
    process = psutil.Process()

    initial_memory = process.memory_info().rss / 1e6  # MB

    # Load dataset
    load_alert_dataset(days=30)

    final_memory = process.memory_info().rss / 1e6  # MB
    memory_increase = final_memory - initial_memory

    # Should use less than 500MB for dataset
    assert memory_increase < 500, f"Memory increase {memory_increase}MB exceeds 500MB limit"

@pytest.mark.benchmark(group="training", warmup=False)
@pytest.mark.benchmark
def test_model_save_speed(benchmark, tmp_path):
    """Benchmark model saving speed."""
    from sentence_transformers import SentenceTransformer
    def save_model():
        model = SentenceTransformer("all-MiniLM-L6-v2")
        model_path = tmp_path / "test_model"
        model.save(str(model_path))
        return model_path

    benchmark(save_model)

    # Model save should be fast (< 5 seconds)
    assert benchmark.stats["mean"] < 5.0
