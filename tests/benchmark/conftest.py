import pytest

def pytest_addoption(parser):
    """Add command line option to run benchmarks."""
    parser.addoption(
        "--run-benchmark", action="store_true", default=False, help="run benchmark tests"
    )

def pytest_configure(config):
    """Add benchmark marker to pytest."""
    config.addinivalue_line("markers", "benchmark: mark test as a benchmark test")

def pytest_collection_modifyitems(config, items):
    """Skip benchmark tests by default.

    Benchmark tests require a controlled environment with specific
    dependencies and resources. See README_benchmark.md for details.

    To run benchmark tests explicitly:
        pytest --run-benchmark -m benchmark
    """
    run_benchmarks = config.getoption("--run-benchmark")

    for item in items:
        if "benchmark" in item.nodeid:
            # Add the benchmark marker for explicit selection
            item.add_marker(pytest.mark.benchmark)

            # Skip if not explicitly requesting benchmark tests
            if not run_benchmarks:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Benchmark tests require controlled environment. Run with --run-benchmark to execute. See README_benchmark.md"
                    )
                )
