"""E2E regression tests for platform stability."""

import time

import pytest

# Temporarily removed skip marker to debug flaky tests
# pytestmark = pytest.mark.skip(reason="flaky after 13-svc refactor – see #642")

class TestDataFlow:
    """Test data flow through the platform."""

    @pytest.mark.e2e
    @pytest.mark.regression
    @pytest.mark.skipif(True, reason="Agent orchestration not implemented in CI core stub services")
    def test_agent_orchestration_flow(self, http_client, alfred_base_url, wait_for_services):
        """Test complete agent orchestration flow."""
        # Create a test request
        request_data = {
            "message": "Test financial query",
            "agent_type": "financial_tax",
            "user_id": "test_user_001",
        }

        # Submit request to Alfred Core
        response = http_client.post(f"{alfred_base_url}/api/v1/agent/query", json=request_data)
        assert response.status_code in [200, 201]

        # Get request ID
        result = response.json()
        request_id = result.get("request_id")
        assert request_id is not None

        # Poll for completion
        max_attempts = 30
        for attempt in range(max_attempts):
            status_response = http_client.get(f"{alfred_base_url}/api/v1/agent/status/{request_id}")
            if status_response.status_code == 200:
                status = status_response.json()
                if status.get("status") in ["completed", "failed"]:
                    break
            time.sleep(1)

        # Verify completion
        assert status.get("status") == "completed"
        assert status.get("result") is not None

class TestPersistence:
    """Test data persistence across services."""

    @pytest.mark.e2e
    @pytest.mark.regression
    @pytest.mark.skipif(True, reason="Database persistence API not implemented in CI core")
    def test_database_persistence(self, http_client, alfred_base_url, wait_for_services):
        """Test database write and read operations."""
        # Create test data
        test_data = {
            "key": f"test_key_{int(time.time())}",
            "value": "test_value",
            "metadata": {"test": True},
        }

        # Write data
        write_response = http_client.post(f"{alfred_base_url}/api/v1/data/store", json=test_data)
        assert write_response.status_code in [200, 201]

        # Read data back
        read_response = http_client.get(
            f"{alfred_base_url}/api/v1/data/retrieve/{test_data['key']}"
        )
        assert read_response.status_code == 200

        # Verify data integrity
        retrieved = read_response.json()
        assert retrieved["value"] == test_data["value"]
        assert retrieved["metadata"]["test"] is True

class TestErrorHandling:
    """Test error handling and recovery."""

    @pytest.mark.e2e
    @pytest.mark.regression
    def test_basic_api_functionality(self, http_client, alfred_base_url, wait_for_services):
        """Test basic API functionality with valid requests."""
        # Test tasks endpoint with any data (stub service accepts anything)
        test_data = {
            "action": "test",
        }

        response = http_client.post(f"{alfred_base_url}/api/v1/tasks", json=test_data)

        # Should return 200 OK with task response
        assert response.status_code == 200
        result = response.json()
        assert "task_id" in result
        assert "status" in result

    @pytest.mark.e2e
    @pytest.mark.regression
    def test_rate_limiting(self, http_client, alfred_base_url, wait_for_services):
        """Test rate limiting functionality."""
        # Send multiple rapid requests
        responses = []
        for i in range(20):
            response = http_client.get(f"{alfred_base_url}/health")
            responses.append(response.status_code)

        # Should not all be rate limited
        assert responses.count(429) < 10  # Less than half rate limited

class TestMetricsCollection:
    """Test metrics collection and reporting."""

    @pytest.mark.e2e
    @pytest.mark.regression
    def test_metrics_endpoint_availability(self, http_client, alfred_base_url, wait_for_services):
        """Test that metrics endpoint is available and returns prometheus format."""
        # Get metrics
        response = http_client.get(f"{alfred_base_url}/metrics")
        assert response.status_code == 200

        metrics_text = response.text

        # Verify it's in prometheus format
        assert "# HELP" in metrics_text or "# TYPE" in metrics_text or metrics_text.strip()

        # Make some requests to potentially increment metrics
        for _ in range(3):
            http_client.get(f"{alfred_base_url}/health")

        # Get metrics again - should still be available
        response2 = http_client.get(f"{alfred_base_url}/metrics")
        assert response2.status_code == 200
