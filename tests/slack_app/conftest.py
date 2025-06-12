"""Configuration for slack_app tests."""

import sys
from pathlib import Path

# Add the project root to sys.path to ensure imports work
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest

def pytest_collection_modifyitems(config, items):
    """Mark slack_app tests as xfail for SC-320.

    These tests require Slack authentication that is not available in the CI environment.
    We'll address these in a dedicated follow-up ticket #220.
    """
    for item in items:
        # Skip already marked tests
        if any(mark.name == "xfail" for mark in item.iter_markers()):
            continue

        # Mark all slack app tests as xfail
        item.add_marker(
            pytest.mark.xfail(
                reason="Slack authentication error in CI environment, see issue #220",
                strict=False,
            )
        )
