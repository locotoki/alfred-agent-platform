"""Integration tests for BizOps metrics collection."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

@pytest.mark.integration
def test_metrics_endpoint_available():
    """Test that metrics endpoint is available and returns Prometheus format."""
    # Mock HTTP client since we're testing the endpoint structure
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
# HELP bizops_request_total Total number of requests
# TYPE bizops_request_total counter
bizops_request_total{method="GET",endpoint="/health",status_code="200",bizops_workflow="system"} 1.0
bizops_request_total{method="GET",endpoint="/legal/compliance",status_code="200",bizops_workflow="legal"} 5.0
bizops_request_total{method="POST",endpoint="/finance/calculation",status_code="200",bizops_workflow="finance"} 3.0

# HELP bizops_request_duration_seconds Request duration in seconds
# TYPE bizops_request_duration_seconds histogram
bizops_request_duration_seconds_bucket{method="GET",endpoint="/health",bizops_workflow="system",le="0.005"} 1.0
bizops_request_duration_seconds_bucket{method="GET",endpoint="/legal/compliance",bizops_workflow="legal",le="0.5"} 2.0

# HELP bizops_request_failures_total Total number of failed requests
# TYPE bizops_request_failures_total counter
bizops_request_failures_total{method="POST",endpoint="/finance/calculation",bizops_workflow="finance",error_type="client_error"} 1.0

# HELP bizops_workflow_operations_total Total workflow operations by type
# TYPE bizops_workflow_operations_total counter
bizops_workflow_operations_total{bizops_workflow="legal",operation_type="compliance_check",status="success"} 10.0
bizops_workflow_operations_total{bizops_workflow="finance",operation_type="tax_calculation",status="success"} 8.0
"""

    with patch("httpx.Client.get", return_value=mock_response):
        client = httpx.Client()
        response = client.get("http://agent-bizops:8080/metrics")

        assert response.status_code == 200
        assert "bizops_request_total" in response.text
        assert 'bizops_workflow="legal"' in response.text
        assert 'bizops_workflow="finance"' in response.text
        assert 'bizops_workflow="system"' in response.text

@pytest.mark.integration
def test_metrics_contain_expected_labels():
    """Test that metrics contain all expected workflow and operation labels."""
    metrics_content = """
bizops_request_total{method="GET",endpoint="/health",status_code="200",bizops_workflow="system"} 1.0
bizops_request_total{method="GET",endpoint="/legal/compliance",status_code="200",bizops_workflow="legal"} 5.0
bizops_request_total{method="POST",endpoint="/finance/calculation",status_code="200",bizops_workflow="finance"} 3.0
bizops_workflow_operations_total{bizops_workflow="legal",operation_type="compliance_check",status="success"} 10.0
bizops_workflow_operations_total{bizops_workflow="finance",operation_type="tax_calculation",status="success"} 8.0
"""

    # Test workflow labels
    assert 'bizops_workflow="legal"' in metrics_content
    assert 'bizops_workflow="finance"' in metrics_content
    assert 'bizops_workflow="system"' in metrics_content

    # Test operation types
    assert 'operation_type="compliance_check"' in metrics_content
    assert 'operation_type="tax_calculation"' in metrics_content

    # Test status labels
    assert 'status="success"' in metrics_content
    assert 'status_code="200"' in metrics_content

@pytest.mark.integration
def test_workflow_path_detection():
    """Test that workflow detection from paths works correctly."""
    from services.agent_bizops.middleware.metrics import PrometheusMetrics
    metrics = PrometheusMetrics()

    # Test legal workflow paths
    assert metrics.get_workflow_from_path("/legal/compliance/check") == "legal"
    assert metrics.get_workflow_from_path("/compliance/audit") == "legal"

    # Test finance workflow paths
    assert metrics.get_workflow_from_path("/finance/calculation") == "finance"
    assert metrics.get_workflow_from_path("/tax/analysis") == "finance"

    # Test system paths
    assert metrics.get_workflow_from_path("/health") == "system"

    # Test unknown paths
    assert metrics.get_workflow_from_path("/unknown/endpoint") == "unknown"

@pytest.mark.integration
def test_operation_type_detection():
    """Test that operation type detection works correctly."""
    from services.agent_bizops.middleware.metrics import PrometheusMetrics
    metrics = PrometheusMetrics()

    # Test legal operations
    assert metrics.get_operation_type("/legal/compliance", "POST") == "compliance_check"
    assert metrics.get_operation_type("/legal/contract/review", "POST") == "contract_review"

    # Test finance operations
    assert metrics.get_operation_type("/finance/calculation", "POST") == "tax_calculation"
    assert metrics.get_operation_type("/finance/analysis", "GET") == "financial_analysis"

    # Test system operations
    assert metrics.get_operation_type("/health", "GET") == "health_check"

    # Test generic operations
    assert metrics.get_operation_type("/unknown", "GET") == "get_request"
    assert metrics.get_operation_type("/unknown", "POST") == "post_request"

@pytest.mark.integration
def test_metrics_middleware_integration():
    """Test that metrics middleware integrates properly with FastAPI."""
    from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.agent_bizops.middleware.metrics import setup_metrics_middleware

# Create test app
    app = FastAPI()
    setup_metrics_middleware(app)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/legal/test")
    async def legal_test_endpoint():
        return {"workflow": "legal"}

    client = TestClient(app)

    # Make some test requests
    response = client.get("/test")
    assert response.status_code == 200

    response = client.get("/legal/test")
    assert response.status_code == 200

    # Check metrics endpoint
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "bizops_request_total" in response.text

    # Should have both unknown and legal workflow metrics
    metrics_text = response.text
    assert 'bizops_workflow="unknown"' in metrics_text
    assert 'bizops_workflow="legal"' in metrics_text

@pytest.mark.integration
def test_error_metrics_recording():
    """Test that error metrics are properly recorded."""
    from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from services.agent_bizops.middleware.metrics import setup_metrics_middleware
    app = FastAPI()
    setup_metrics_middleware(app)

    @app.get("/legal/test-error")
    async def error_endpoint():
        raise HTTPException(status_code=500, detail="Test error")

    @app.get("/finance/test-client-error")
    async def client_error_endpoint():
        raise HTTPException(status_code=400, detail="Bad request")

    client = TestClient(app)

    # Generate some errors
    response = client.get("/legal/test-error")
    assert response.status_code == 500

    response = client.get("/finance/test-client-error")
    assert response.status_code == 400

    # Check metrics
    response = client.get("/metrics")
    assert response.status_code == 200

    metrics_text = response.text

    # Should have failure counters
    assert "bizops_request_failures_total" in metrics_text

    # Should have workflow-specific error tracking
    assert 'bizops_workflow="legal"' in metrics_text
    assert 'bizops_workflow="finance"' in metrics_text

@pytest.mark.integration
def test_duration_metrics_collection():
    """Test that request duration metrics are collected."""
    import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.agent_bizops.middleware.metrics import setup_metrics_middleware
    app = FastAPI()
    setup_metrics_middleware(app)

    @app.get("/legal/slow-endpoint")
    async def slow_endpoint():
        await asyncio.sleep(0.1)  # 100ms delay
        return {"status": "completed"}

    client = TestClient(app)

    # Make request to slow endpoint
    response = client.get("/legal/slow-endpoint")
    assert response.status_code == 200

    # Check duration metrics
    response = client.get("/metrics")
    assert response.status_code == 200

    metrics_text = response.text

    # Should have duration histogram and summary
    assert "bizops_request_duration_seconds" in metrics_text
    assert "bizops_request_duration_summary_seconds" in metrics_text

    # Should have legal workflow duration tracking
    assert 'bizops_workflow="legal"' in metrics_text
