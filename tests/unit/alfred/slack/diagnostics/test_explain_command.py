"""Unit tests for the explain command handler."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.xfail(reason="SC-330 async bug", strict=False)
from alfred.slack.diagnostics.explain_command import handle_explain_command

async def test_handle_explain_command_success():
    """Test successful explain command handling."""
    result = await handle_explain_command("explain", "ALERT-123")

    assert result["response_type"] == "in_channel"
    assert "Alert Explanation for ALERT-123" in result["text"]
    assert len(result["attachments"]) == 1
    assert result["attachments"][0]["color"] == "good"
    assert "alert indicates" in result["attachments"][0]["text"].lower()

@patch("alfred.slack.diagnostics.explain_command.ExplainerAgent")
async def test_handle_explain_command_failure(mock_agent_cls):
    """Test explain command handling when agent fails."""
    mock_agent = Mock()
    mock_agent.explain_alert = AsyncMock(
        return_value={
            "success": False,
            "explanation": "Error: LLM not available",
        }
    )
    mock_agent_cls.return_value = mock_agent

    result = await handle_explain_command("explain", "ALERT-456")

    assert result["response_type"] == "ephemeral"
    assert "Failed to explain alert ALERT-456" in result["text"]
    assert "Error: LLM not available" in result["text"]
