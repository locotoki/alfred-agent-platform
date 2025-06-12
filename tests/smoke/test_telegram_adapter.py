"""Smoke tests for Telegram Adapter.

This module contains basic smoke tests for the Telegram Adapter service.
"""

import os

import pytest
import requests

# Mark all tests in this module as smoke tests
pytestmark = pytest.mark.smoke
def get_adapter_url() -> str:
    """Get the URL for the Telegram adapter service."""
    return os.environ.get("TELEGRAM_ADAPTER_URL", "http://localhost:3002")

@pytest.fixture
def adapter_url() -> str:
    """Fixture that returns the URL for the Telegram adapter."""
    return get_adapter_url()

def test_health_endpoint(adapter_url: str) -> None:
    """Test that the health endpoint returns a 200 status code."""
    response = requests.get(f"{adapter_url}/health", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "telegram-adapter"

def test_metrics_endpoint(adapter_url: str) -> None:
    """Test that the metrics endpoint returns a 200 status code."""
    response = requests.get(f"{adapter_url}/metrics", timeout=5)
    assert response.status_code == 200
    # Prometheus metrics are returned as text
    assert "telegram_adapter_requests_total" in response.text

def test_webhook_post(adapter_url: str) -> None:
    """Test that the webhook endpoint accepts POST requests."""
    # Minimal valid Telegram Update object
    update_data = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "date": 1621234567,
            "chat": {"id": 123456789, "type": "private"},
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user",
            },
            "text": "Hello, bot!",
        },
    }

    response = requests.post(f"{adapter_url}/telegram/webhook", json=update_data, timeout=5)

    # The webhook should always return a 200 status code to Telegram
    assert response.status_code == 200
    assert response.json() is not None
