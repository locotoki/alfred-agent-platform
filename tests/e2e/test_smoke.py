"""E2E smoke tests for core services."""

import pytest

# Temporarily removed skip marker to debug flaky tests
# pytestmark = pytest.mark.skip(reason="flaky after 13-svc refactor – see #642")

class TestCoreServices:
    """Test core service health endpoints."""

    @pytest.mark.e2e
    def test_agent_core_health(self, http_client, wait_for_services):
        """Test Agent Core health endpoint."""
        response = http_client.get("http://localhost:8011/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.e2e
    @pytest.mark.skip(
        reason="model-registry is a stub service (sleep infinity) without real health endpoint"
    )
    def test_model_registry_health(self, http_client, wait_for_services):
        """Test Model Registry health endpoint."""
        response = http_client.get("http://localhost:8079/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.e2e
    def test_db_api_health(self, http_client, wait_for_services):
        """Test DB API connectivity."""
        # db-api doesn't have a health endpoint, just test it responds
        response = http_client.get("http://localhost:3000/")
        assert response.status_code == 200

    @pytest.mark.e2e
    def test_pubsub_metrics_health(self, http_client, wait_for_services):
        """Test PubSub Metrics endpoint."""
        response = http_client.get("http://localhost:9103/metrics")
        assert response.status_code == 200
        # Should contain prometheus metrics
        assert "# HELP" in response.text

    @pytest.mark.e2e
    @pytest.mark.skip(reason="agent-core service doesn't expose database connectivity info")
    def test_database_connectivity(self, http_client, wait_for_services):
        """Test database connectivity through Agent Core."""
        response = http_client.get("http://localhost:8011/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["postgres"]["status"] == "connected"
        assert data["redis"]["status"] == "connected"

class TestMetricsEndpoints:
    """Test metrics endpoints."""

    @pytest.mark.e2e
    def test_prometheus_metrics(self, http_client, wait_for_services):
        """Test Prometheus metrics endpoints."""
        # Updated to match actual CI core services
        services = [
            ("agent-core", 8011),
            ("pubsub-metrics", 9103),
            ("redis-exporter", 9101),
        ]

        for service, port in services:
            response = http_client.get(f"http://localhost:{port}/metrics")
            assert response.status_code == 200
            # Different services expose different metrics
            if service == "redis-exporter":
                assert "redis_" in response.text
            else:
                assert "# HELP" in response.text  # Standard prometheus format

class TestSlackIntegration:
    """Test Slack integration."""

    @pytest.mark.e2e
    @pytest.mark.skipif(
        True, reason="Slack tests disabled by default - use --slack-tests to enable"
    )
    def test_slack_webhook(self, http_client, slack_webhook_url):
        """Test Slack webhook connectivity."""
        if not slack_webhook_url:
            pytest.skip("No Slack webhook URL configured")

        payload = {
            "text": "E2E test message",
            "channel": "#test-alerts",
        }
        response = http_client.post(slack_webhook_url, json=payload)
        assert response.status_code == 200
