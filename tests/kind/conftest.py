import pytest

def pytest_collection_modifyitems(config, items):
    """Skip kind tests for SC-320."""
    for item in items:
        # Skip already marked tests
        if any(mark.name == "xfail" for mark in item.iter_markers()):
            continue

        # Add xfail marker to all tests in this directory
        item.add_marker(
            pytest.mark.xfail(
                reason="Kind tests need Kubernetes environment, see issue #220", strict=False
            )
        )
