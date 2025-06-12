"""Unit tests for the health module."""

import pytest
from fastapi.testclient import TestClient

from libs.agent_core.health import create_health_app
from libs.agent_core.health.dependency_tracker import DependencyTracker

@pytest.fixture
def health_app():
    """Create a health app for testing."""
    return create_health_app("test-service", "1.0.0")

@pytest.fixture
def client(health_app):
    """Create a test client for the health app."""
    return TestClient(health_app)

def test_health_endpoint(client):
    """Test the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "services" in data

def test_healthz_endpoint(client):
    """Test the /healthz endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_metrics_endpoint(client):
    """Test the /metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    # Verify this is valid Prometheus metrics output
    assert "# HELP" in response.text
    assert "# TYPE" in response.text

def test_legacy_endpoints(client):
    """Test the legacy endpoints for backward compatibility."""
    # Root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "test-service"
    assert data["version"] == "1.0.0"

    # Ready endpoint
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"

    # Live endpoint
    response = client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"

def test_dependency_tracking(health_app, client):
    """Test dependency tracking functionality."""
    # Register dependencies
    health_app.register_dependency("database", "ok")
    health_app.register_dependency("external-api", "ok")

    # Verify dependencies are tracked
    response = client.get("/health")
    data = response.json()
    assert data["services"]["database"] == "ok"
    assert data["services"]["external-api"] == "ok"

    # Update dependency status
    health_app.update_dependency_status("database", "error")

    # Verify status is updated
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "error"
    assert data["services"]["database"] == "error"
    assert data["services"]["external-api"] == "ok"

def test_dependency_tracker_class():
    """Test the DependencyTracker class directly."""
    tracker = DependencyTracker("test-service")

    # Register dependencies
    tracker.register_dependency("db", "ok")
    tracker.register_dependency("api", "ok")

    # Check dependencies
    deps = tracker.check_dependencies()
    assert deps["db"] == "ok"
    assert deps["api"] == "ok"

    # Update dependency
    tracker.update_dependency_status("db", "error")
    deps = tracker.check_dependencies()
    assert deps["db"] == "error"

    # Update non-existent dependency should not raise error
    tracker.update_dependency_status("non-existent", "error")
    deps = tracker.check_dependencies()
    assert "non-existent" not in deps
