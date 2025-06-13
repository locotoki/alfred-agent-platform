"""Tests for string utility functions."""

from alfred.utils.string_utils import split_text, truncate

def test_truncate_no_truncation_needed() -> None:
    """Test truncation when the string is short enough."""
    result = truncate("Short string", max_length=20)
    assert result == "Short string"
    assert len(result) <= 20

def test_truncate_with_truncation() -> None:
    """Test truncation when the string exceeds max length."""
    long_string = "This is a very long string that needs to be truncated"
    result = truncate(long_string, max_length=20)
    assert result.endswith("...")
    assert len(result) <= 20
    assert result == "This is a very lo..."

def test_truncate_custom_suffix() -> None:
    """Test truncation with a custom suffix."""
    result = truncate("Truncate this text", max_length=10, suffix="[...]")
    assert result.endswith("[...]")
    assert len(result) <= 10
    assert result == "Trunc[...]"

def test_split_text_small_text() -> None:
    """Test splitting when text is smaller than chunk size."""
    text = "Small text"
    chunks = split_text(text, chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_split_text_breaking_at_spaces() -> None:
    """Test splitting text and breaking at spaces."""
    text = "This is a longer text that should be split into multiple chunks"
    chunks = split_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1

    # Check first chunk ends with a space
    assert chunks[0].endswith(" ")

    # Check overlap
    assert chunks[0][-5:] in chunks[1]

def test_split_text_breaking_at_newlines() -> None:
    """Test splitting text and breaking at newlines."""
    text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    chunks = split_text(text, chunk_size=12, overlap=3)
    assert len(chunks) > 1

    # Check first chunk ends with a newline
    assert chunks[0].endswith("\n")

    # Check overlap
    assert chunks[0][-3:] in chunks[1]
