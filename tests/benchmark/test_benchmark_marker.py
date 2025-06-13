"""
Benchmark tests marker file.

This file exists to verify the benchmark test configuration works correctly.
Benchmark tests are skipped by default and can be run explicitly with pytest --run-benchmark -m benchmark.
"""

import pytest

@pytest.mark.benchmark
def test_benchmark_marker_exists():
    """Ensure benchmark test marker exists.

    This test can be used to verify the benchmark test configuration:

    * It should be skipped by default
    * It should run when called with `pytest --run-benchmark -m benchmark`
    * It should always pass when run

    To run specific benchmark tests, use:
    pytest --run-benchmark -m benchmark
    """
    assert True, "Benchmark marker is working correctly"
