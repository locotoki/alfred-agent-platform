"""Import guard test for ui-chat streamlit module."""

import os
import sys

import pytest

# Skip if running in CI without streamlit installed
if os.getenv("CI"):
    pytest.skip("Streamlit not available in CI", allow_module_level=True)

def test_streamlit_chat_imports():
    """Test that streamlit_chat module can be imported."""
    # Add alfred/ui to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../alfred/ui"))

    # This should not raise ImportError

    import streamlit_chat

# Basic validation
    assert streamlit_chat is not None
