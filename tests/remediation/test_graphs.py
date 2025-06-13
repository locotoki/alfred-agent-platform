"""Tests for remediation graphs.

This module provides unit tests for the remediation graph workflows, ensuring that the
LangGraph-based remediation processes work correctly.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from alfred.remediation import settings
from alfred.remediation.graphs import (
    
,
    complete_remediation,
    escalate_issue,
    probe_health,
    restart_service,
    restart_then_verify,
    should_retry_or_complete,
    wait_for_stabilization,
)

@pytest.fixture
def basic_state():
    """Basic remediation state for testing."""
    return {
        "service_name": "test-service",
        "wait_seconds": 5,
        "max_retries": 3,
        "retry_count": 0,
        "start_timestamp": time.time(),
    }

@pytest.fixture
def mock_requests():
    with patch("remediation.graphs.requests") as mock:
        # Configure mock responses for different endpoints
        restart_response = MagicMock()
        restart_response.status_code = 200

        health_response = MagicMock()
        health_response.status_code = 200
        health_response.text = '{"status": "healthy"}'

        mock.post.return_value = restart_response
        mock.get.return_value = health_response

        yield mock

@patch("remediation.settings.get_webhook_url")
def test_restart_service_success(mock_get_webhook, basic_state, mock_requests):
    """Test successful service restart."""
    webhook_url = "http://n8n:5678/webhook/restart-service"
    mock_get_webhook.return_value = webhook_url

    result = restart_service(basic_state)

    # Verify API call
    mock_requests.post.assert_called_once_with(
        webhook_url, json={"service": "test-service"}, timeout=settings.PROBE_TIMEOUT
    )

    # Verify state updates
    assert result["restart_status"] == "success"
    assert "restart_timestamp" in result

@patch("remediation.settings.get_webhook_url")
def test_restart_service_failure(mock_get_webhook, basic_state, mock_requests):
    """Test failed service restart."""
    webhook_url = "http://n8n:5678/webhook/restart-service"
    mock_get_webhook.return_value = webhook_url
    mock_requests.post.side_effect = Exception("Connection error")

    result = restart_service(basic_state)

    # Verify state updates for failure
    assert result["restart_status"] == "failed"
    assert result["error"] == "Connection error"

@patch("remediation.graphs.time.sleep")
def test_wait_for_stabilization(mock_sleep, basic_state):
    """Test waiting for service stabilization."""
    result = wait_for_stabilization(basic_state)

    # Verify sleep was called with the value from state
    mock_sleep.assert_called_once_with(5)

    # Verify state updates
    assert result["wait_completed"] is True
    assert "wait_timestamp" in result

@patch("remediation.graphs.time.sleep")
def test_wait_for_stabilization_default(mock_sleep):
    """Test waiting for service stabilization with default value."""
    state = {"service_name": "test-service"}
    result = wait_for_stabilization(state)

    # Verify sleep was called with the default value
    mock_sleep.assert_called_once_with(settings.DEFAULT_WAIT_SECONDS)

    # Verify state updates
    assert result["wait_completed"] is True
    assert "wait_timestamp" in result

def test_probe_health_success(basic_state, mock_requests):
    """Test successful health probe."""
    mock_requests.get.return_value.status_code = 200

    result = probe_health(basic_state)

    # Verify API call
    mock_requests.get.assert_called_once_with(
        "http://test-service:8080/health", timeout=settings.PROBE_TIMEOUT
    )

    # Verify state updates
    assert result["probe_status_code"] == 200
    assert result["health_ok"] is True
    assert "probe_timestamp" in result

def test_probe_health_failure(basic_state, mock_requests):
    """Test failed health probe."""
    mock_requests.get.return_value.status_code = 500

    result = probe_health(basic_state)

    # Verify state updates for failure
    assert result["probe_status_code"] == 500
    assert result["health_ok"] is False

def test_probe_health_exception(basic_state, mock_requests):
    """Test exception during health probe."""
    error_message = "Connection refused"
    mock_requests.get.side_effect = Exception(error_message)

    result = probe_health(basic_state)

    # Verify state updates for exception
    assert result["probe_status_code"] == 500
    assert result["health_ok"] is False
    assert result["probe_response"] == error_message
    assert result["probe_error"] == error_message  # Verify error is exposed

@patch("remediation.settings.MAX_RETRIES", 5)  # Override for this test
def test_should_retry_or_complete_with_settings():
    """Test decision function using settings for max retries."""
    state = {
        "health_ok": False,
        "retry_count": 4,
    }

    result = should_retry_or_complete(state)

    # Should still retry because MAX_RETRIES is now 5
    assert result == "retry"
    assert state["retry_count"] == 5

def test_should_retry_or_complete_success():
    """Test decision function when health is ok."""
    state = {"health_ok": True, "retry_count": 1, "max_retries": 3}

    result = should_retry_or_complete(state)

    assert result == "complete"

def test_should_retry_or_complete_retry():
    """Test decision function when health not ok but retries available."""
    state = {"health_ok": False, "retry_count": 1, "max_retries": 3}

    result = should_retry_or_complete(state)

    assert result == "retry"
    assert state["retry_count"] == 2  # Incremented

def test_should_retry_or_complete_escalate():
    """Test decision function when max retries reached."""
    state = {"health_ok": False, "retry_count": 3, "max_retries": 3}

    result = should_retry_or_complete(state)

    assert result == "escalate"

def test_complete_remediation(basic_state):
    """Test successful remediation completion."""
    basic_state["thread_ts"] = "1234567890.123456"
    basic_state["channel"] = "C12345"

    result = complete_remediation(basic_state)

    assert result["remediation_status"] == "success"
    assert result["remediation_completed"] is True
    assert result["thread_updated"] is True
    assert "completion_message" in result

def test_escalate_issue(basic_state):
    """Test issue escalation."""
    basic_state["thread_ts"] = "1234567890.123456"
    basic_state["channel"] = "C12345"
    basic_state["retry_count"] = 3

    result = escalate_issue(basic_state)

    assert result["remediation_status"] == "escalated"
    assert result["remediation_completed"] is True
    assert result["thread_updated"] is True
    assert "escalation_message" in result

def test_escalate_issue_with_error(basic_state):
    """Test issue escalation with probe error."""
    basic_state["thread_ts"] = "1234567890.123456"
    basic_state["channel"] = "C12345"
    basic_state["retry_count"] = 3
    basic_state["probe_error"] = "Connection timeout"

    result = escalate_issue(basic_state)

    # Verify error is included in escalation message
    assert "Last error: Connection timeout" in result["escalation_message"]
    assert result["remediation_status"] == "escalated"

@patch("remediation.graphs.time.sleep")
@patch("remediation.settings.get_webhook_url")
def test_restart_then_verify_graph_success(mock_get_webhook, mock_sleep, mock_requests):
    """Test successful execution of the full graph."""
    webhook_url = "http://n8n:5678/webhook/restart-service"
    mock_get_webhook.return_value = webhook_url

    # Configure for successful remediation
    mock_requests.get.return_value.status_code = 200

    # Create graph
    graph, initial_state = restart_then_verify("test-service", wait_seconds=1)

    # Run the graph
    result = graph.invoke(initial_state)

    # Verify the final state contains success markers
    assert result["remediation_status"] == "success"
    assert result["remediation_completed"] is True
    assert result["health_ok"] is True

@patch("remediation.graphs.time.sleep")
@patch("remediation.settings.get_webhook_url")
def test_restart_then_verify_graph_retry_then_success(mock_get_webhook, mock_sleep, mock_requests):
    """Test graph with one failed attempt then success."""
    webhook_url = "http://n8n:5678/webhook/restart-service"
    mock_get_webhook.return_value = webhook_url

    # First health probe fails, second succeeds
    responses = [MagicMock(), MagicMock()]
    responses[0].status_code = 500
    responses[1].status_code = 200
    mock_requests.get.side_effect = responses

    # Create graph
    graph, initial_state = restart_then_verify("test-service", wait_seconds=1)

    # Run the graph
    result = graph.invoke(initial_state)

    # Verify retry occurred then succeeded
    assert result["retry_count"] == 1
    assert result["remediation_status"] == "success"
    assert result["remediation_completed"] is True
    assert result["health_ok"] is True

@patch("remediation.graphs.time.sleep")
@patch("remediation.settings.get_webhook_url")
def test_restart_then_verify_graph_escalation(mock_get_webhook, mock_sleep, mock_requests):
    """Test graph escalation after max retries."""
    webhook_url = "http://n8n:5678/webhook/restart-service"
    mock_get_webhook.return_value = webhook_url

    # All health probes fail
    mock_requests.get.return_value.status_code = 500

    # Create graph with fewer retries for faster testing
    graph, initial_state = restart_then_verify("test-service", wait_seconds=1, max_retries=2)

    # Run the graph
    result = graph.invoke(initial_state)

    # Verify escalation after retries
    assert result["retry_count"] == 2  # Hit max retries
    assert result["remediation_status"] == "escalated"
    assert result["remediation_completed"] is True
    assert result["health_ok"] is False

@patch("remediation.settings.MAX_RETRIES", 5)
@patch("remediation.settings.DEFAULT_WAIT_SECONDS", 10)
@patch("remediation.graphs.time.sleep")
@patch("remediation.settings.get_webhook_url")
def test_restart_then_verify_with_default_settings(mock_get_webhook, mock_sleep, mock_requests):
    """Test graph using environment settings."""
    webhook_url = "http://n8n:5678/webhook/restart-service"
    mock_get_webhook.return_value = webhook_url

    # Create graph with default settings
    graph, initial_state = restart_then_verify("test-service")

    # Check that initial state reflects environment settings
    assert initial_state["max_retries"] == 5
    assert initial_state["wait_seconds"] == 10
