"""Configuration for alfred/ml tests."""

import sys
from pathlib import Path

# Add the project root to sys.path to ensure imports work
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest

def pytest_collection_modifyitems(config, items):
    """Mark alfred/ml tests as xfail for SC-320.

    These tests require specific ML dependencies that are not available in the CI environment.
    We'll address these in a dedicated follow-up ticket #220.
    """
    # Categorize specific test modules by their dependencies
    sentence_transformers_dependent_tests = [
        "test_hf_embedder",
        "test_thresholds",
    ]

    for item in items:
        # Skip already marked tests
        if any(mark.name == "xfail" for mark in item.iter_markers()):
            continue

        # Apply specific markers based on test dependencies
        if any(test_name in item.nodeid for test_name in sentence_transformers_dependent_tests):
            item.add_marker(
                pytest.mark.xfail(
                    reason="Missing sentence_transformers dependency, see issue #220",
                    strict=False,
                )
            )
