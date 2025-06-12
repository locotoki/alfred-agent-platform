"""Test CRM sync service dependencies."""

def test_attrs_importable():
    """Ensure attrs is available at runtime."""
    import attrs  # noqa: F401
