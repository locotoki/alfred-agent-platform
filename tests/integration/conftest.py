"""Global fixtures and configuration for integration tests."""

import pytest

# Mark failing tests as xfail with appropriate issue references
def pytest_configure(config):
    """Configure pytest for integration tests."""
    config.addinivalue_line(
        "markers",
        "xfail_known_issue(reason, issue): mark test as xfail due to a known issue",
    )
    # Add a new marker for flaky tests that need multiple runs
    config.addinivalue_line(
        "markers",
        "flaky(reruns=int): mark test as flaky and retry a given number of times",
    )

# Handle flaky tests with reruns
def pytest_collection_modifyitems(config, items):
    """Apply flaky marks to tests that need them."""
    # The following tests may occasionally be flaky, so we'll mark them for reruns
    flaky_tests = [
        # Explainer smoke test - occasionally flaky due to service startup timing
        ("test_explainer_smoke", 3),
    ]

    for item in items:
        for name, reruns in flaky_tests:
            if name in item.name and "test_explainer_smoke" in item.name:
                item.add_marker(pytest.mark.flaky(reruns=reruns))
