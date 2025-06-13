import os

import psutil
import pytest
from fastapi.testclient import TestClient

from services.health.cpu import app

@pytest.fixture(autouse=True)
def patch_cpu_and_loadavg(monkeypatch):
    """Patch psutil.cpu_percent and os.getloadavg to deterministic values for
    testing."""
    monkeypatch.setattr(psutil, "cpu_percent", lambda: 42.5)
    monkeypatch.setattr(os, "getloadavg", lambda: (1.1, 2.2, 3.3))

@pytest.fixture
def client():
    """Create a FastAPI test client for the CPU probe app."""
    return TestClient(app)

def test_cpu_endpoint_returns_expected_keys_and_values(client):
    """Test GET /cpu returns expected JSON with CPU usage and load averages."""
    response = client.get("/cpu")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "used_percent",
        "load_avg_1m",
        "load_avg_5m",
        "load_avg_15m",
    }
    assert data["used_percent"] == 42.5
    assert data["load_avg_1m"] == 1.1
    assert data["load_avg_5m"] == 2.2
    assert data["load_avg_15m"] == 3.3
