"""Import guard test for crm-sync hubspot_mock_client."""

import os
import sys

def test_hubspot_mock_client_imports():
    """Test that hubspot_mock_client module can be imported."""
    # Add clients directory to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/crm-sync"))

    # This should not raise ImportError

    from clients.hubspot_mock_client import Client, models

# Basic validation
    assert Client is not None
    assert models is not None
