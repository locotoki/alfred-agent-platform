import asyncio
import os
from typing import Generator
from unittest.mock import MagicMock

# Handle asyncpg import for environment where it might not be available
try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None
    import pytest
    pytest.skip("asyncpg not available", allow_module_level=True)

import pytest
import redis
from google.cloud import pubsub_v1

from libs.a2a_adapter import PolicyMiddleware, PubSubTransport, SupabaseTransport

# Global pytest configuration for SC-320
def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--slack-tests", action="store_true", default=False, help="run slack integration tests"
    )

def pytest_configure(config):
    """Configure pytest with markers for SC-320."""
    config.addinivalue_line(
        "markers",
        "benchmark: mark tests that are benchmarks",
    )
    config.addinivalue_line(
        "markers",
        "smoke: mark tests that are smoke tests",
    )

# Apply xfail to specific tests that are known to fail due to unresolved issues
def pytest_collection_modifyitems(config, items):
    """Apply xfail marks to tests that need them for SC-320."""
    # List of specific ML-related failing tests with their reason
    ml_failing_tests = [
        ("test_hf_embedder", "Missing sentence_transformers dependency, see issue #220"),
        ("test_thresholds", "Missing sentence_transformers dependency, see issue #220"),
        ("test_alert_dataset", "Missing faiss dependency, see issue #220"),
        ("test_dataset_db", "Missing ML dependencies, see issue #220"),
        ("test_faiss_index", "Missing faiss dependency, see issue #220"),
        ("test_inference_benchmark", "Missing sentence_transformers dependency, see issue #220"),
        ("test_model_registry", "Missing ML dependencies, see issue #220"),
        ("test_retrain_pipeline", "Missing ML dependencies, see issue #220"),
        ("test_trainer_benchmark", "Missing faiss dependency, see issue #220"),
    ]

    # List of specific Slack-related failing tests
    slack_failing_tests = [
        ("test_command_handler", "Slack authentication error, see issue #220"),
        ("test_startup", "Slack authentication error, see issue #220"),
    ]

    # Categorize failing test file names by type
    for item in items:
        # Skip already marked tests
        if any(mark.name == "xfail" for mark in item.iter_markers()):
            continue

        # Apply specific ML-related xfail markers
        for test_name, reason in ml_failing_tests:
            if test_name in item.nodeid:
                item.add_marker(pytest.mark.xfail(reason=reason, strict=False))
                break

        # Apply specific Slack-related xfail markers
        for test_name, reason in slack_failing_tests:
            if test_name in item.nodeid:
                item.add_marker(pytest.mark.xfail(reason=reason, strict=False))
                break

        # Benchmark tests are now handled in tests/benchmark/conftest.py
        # We no longer apply global xfail markers to benchmark tests

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True, scope="session")
def _patch_slack_env():
    """Set up Slack environment variables for testing."""
    os.environ.setdefault("SLACK_WEBHOOK_URL", "https://example.com/hook")
    os.environ.setdefault("SLACK_CVE_WEBHOOK", "https://example.com/cve-hook")
    os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token")
    os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret")

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/test_db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["GCP_PROJECT_ID"] = "test-project"

@pytest.fixture
async def test_db():
    """Provide a clean test database."""
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])

    # Clean up existing data
    await conn.execute("TRUNCATE TABLE tasks, task_results, processed_messages CASCADE")

    yield conn

    await conn.close()

@pytest.fixture
def mock_pubsub():
    """Mock Pub/Sub client."""
    mock = MagicMock(spec=pubsub_v1.PublisherClient)
    mock.publish.return_value.result.return_value = "test-message-id"
    return mock

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return MagicMock(spec=redis.Redis)

@pytest.fixture
def pubsub_transport(mock_pubsub):
    """Create PubSubTransport with mock."""
    transport = PubSubTransport(project_id="test-project")
    transport.publisher = mock_pubsub
    return transport

@pytest.fixture
async def supabase_transport(test_db):
    """Create SupabaseTransport with test database."""
    transport = SupabaseTransport(database_url=os.environ["DATABASE_URL"])
    await transport.connect()
    yield transport
    await transport.disconnect()

@pytest.fixture
def policy_middleware(mock_redis):
    """Create PolicyMiddleware with mock Redis."""
    return PolicyMiddleware(redis_client=mock_redis)
