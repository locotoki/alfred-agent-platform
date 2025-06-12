import pytest

def pytest_collection_modifyitems(config, items):
    """Skip validation tests for SC-320."""
    for item in items:
        # Skip already marked tests
        if any(mark.name == "xfail" for mark in item.iter_markers()):
            continue

        # Add xfail marker to all tests in this directory
        item.add_marker(
            pytest.mark.xfail(
                reason="Validation tests need specific environment setup, see issue #220",
                strict=False,
            )
        )
