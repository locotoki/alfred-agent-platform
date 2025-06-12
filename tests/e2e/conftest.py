"""E2E test configuration and fixtures."""

import os
import time
from typing import Generator

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

@pytest.fixture(scope="session")
def http_client() -> Generator[requests.Session, None, None]:
    """Create HTTP client with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    yield session
    session.close()

@pytest.fixture(scope="session")
def wait_for_services():
    """Wait for services to be ready."""
    # Updated to match actual working CI core services
    services = {
        "agent-core": "http://localhost:8011/health",
        "db-api": "http://localhost:3000/",  # db-api doesn't have /health endpoint
        "pubsub-metrics": "http://localhost:9103/metrics",  # metrics endpoint
        # Note: model-registry and model-router are stub services running "sleep infinity"
    }

    max_attempts = 30
    for service, url in services.items():
        print(f"Waiting for {service}...")
        for attempt in range(max_attempts):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✓ {service} is ready")
                    break
            except requests.exceptions.RequestException:
                if attempt == max_attempts - 1:
                    pytest.fail(f"Service {service} failed to start")
                time.sleep(2)

@pytest.fixture
def alfred_base_url():
    """Get Alfred API base URL."""
    return os.getenv("A
RED_BASE_URL", "http://localhost:8011")

@pytest.fixture
def slack_webhook_url():
    """Get Slack webhook URL for testing."""
    return os.getenv("SLACK_WEBHOOK_URL", "")
