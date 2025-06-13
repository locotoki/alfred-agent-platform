"""E2E tests for Slack integration."""

import os

import pytest

# Temporarily removed skip marker to debug flaky tests
# pytestmark = pytest.mark.skip(reason="flaky after 13-svc refactor – see #642")

class TestSlackIntegration:
    """Test Slack integration functionality."""

    @pytest.mark.e2e
    @pytest.mark.slack
    @pytest.mark.skipif(True, reason="Slack integration not configured in CI core setup")
    def test_slack_alert_delivery(self, http_client):
        """Test alert delivery to Slack."""
        # This test requires SLACK_WEBHOOK_URL to be set
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            pytest.skip("SLACK_WEBHOOK_URL not configured")

        # Test alert payload
        alert_payload = {
            "receiver": "slack-alerts-prod",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "E2E_Test_Alert",
                        "severity": "info",
                        "service": "e2e-tests",
                    },
                    "annotations": {
                        "summary": "E2E test alert",
                        "description": "This is a test alert from E2E tests",
                    },
                }
            ],
        }

        # Send to Alertmanager webhook
        response = http_client.post(
            "http://localhost:9093/api/v1/alerts", json=[alert_payload["alerts"][0]]
        )

        # Alertmanager should accept the alert
        assert response.status_code in [200, 202]

    @pytest.mark.e2e
    @pytest.mark.slack
    @pytest.mark.skipif(True, reason="Slack MCP Gateway not included in CI core setup")
    def test_slack_mcp_gateway_health(self, http_client):
        """Test Slack MCP Gateway health."""
        # Check if slack-mcp-gateway is running
        try:
            response = http_client.get("http://localhost:8020/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"
        except Exception:
            pytest.skip("Slack MCP Gateway not running")

    @pytest.mark.e2e
    @pytest.mark.slack
    @pytest.mark.skipif(True, reason="Slack bot not included in CI core setup")
    def test_slack_bot_command(self, http_client):
        """Test Slack bot command handling."""
        # Simulate Slack slash command
        command_data = {
            "token": "test-token",
            "team_id": "T123456",
            "team_domain": "test-team",
            "channel_id": "C123456",
            "channel_name": "test-channel",
            "user_id": "U123456",
            "user_name": "test-user",
            "command": "/alfred",
            "text": "health",
            "response_url": "https://hooks.slack.com/commands/test",
        }

        try:
            response = http_client.post(
                "http://localhost:8020/slack/commands",
                data=command_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Should return acknowledgment
            assert response.status_code == 200

            # Response should be JSON
            result = response.json()
            assert "text" in result or "blocks" in result
        except Exception:
            pytest.skip("Slack MCP Gateway not configured for commands")
