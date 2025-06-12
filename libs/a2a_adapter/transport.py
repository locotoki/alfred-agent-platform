"""Stub transport implementation for A2A Adapter."""

from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)
class PubSubTransport:
    """Stub implementation of PubSubTransport for social-intel container."""

    def __init__(self, project_id: str):
        """Initialize PubSubTransport with project ID."""
        self.project_id = project_id
        self.completed_topic_path = "completed-tasks"
        logger.info("Initialized stub PubSubTransport", project_id=project_id)

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        attributes: Optional[Dict[str, str]] = None,
    ) -> str:
        """Stub method to publish a message to a topic."""
        logger.info("STUB: Publishing message to topic", topic=topic)
        return "message-id-stub"

    async def subscribe(
        self, subscription: str, callback: Callable, error_callback: Callable = None
    ):
        """Stub method to subscribe to a topic."""
        logger.info("STUB: Subscribing to topic", subscription=subscription)

    def create_topic(self, topic: str) -> None:
        """Stub method to create a topic."""
        logger.info("STUB: Creating topic", topic=topic)

    def create_subscription(self, subscription: str, topic: str) -> None:
        """Stub method to create a subscription."""
        logger.info("STUB: Creating subscription", subscription=subscription, topic=topic)

    async def publish_task(self, envelope: Any, topic: str = None) -> str:
        """Stub method to publish a task envelope."""
        logger.info(
            "STUB: Publishing task envelope",
            intent=getattr(envelope, "intent", "unknown"),
            topic=topic or "default-topic",
        )
        return "message-id-stub-task"

class SupabaseTransport:
    """Stub implementation of SupabaseTransport for social-intel container."""

    def __init__(self, database_url: str):
        """Initialize SupabaseTransport with database URL."""
        self.database_url = database_url
        self._pool = None  # Add missing _pool attribute required by tests
        logger.info("Initialized stub SupabaseTransport", database_url=database_url)

    async def connect(self) -> None:
        """Stub method to connect to Supabase."""
        logger.info("STUB: Connecting to Supabase")

    async def disconnect(self) -> None:
        """Stub method to disconnect from Supabase."""
        logger.info("STUB: Disconnecting from Supabase")

    async def execute(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """Stub method to execute a query."""
        logger.info("STUB: Executing query", query=query)
        return []

    async def fetch(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """Stub method to fetch data."""
        logger.info("STUB: Fetching data", query=query)
        return []

    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Stub method to fetch a single row."""
        logger.info("STUB: Fetching row", query=query)
        return None

    async def store_task(self, envelope: Any) -> str:
        """Stub method to store a task envelope in the database."""
        logger.info("STUB: Storing task envelope", intent=getattr(envelope, "intent", "unknown"))
        return getattr(envelope, "task_id", "task-id-stub")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Stub method to get the status of a task."""
        logger.info("STUB: Getting task status", task_id=task_id)
        return {
            "task_id": task_id,
            "status": "pending",
            "created_at": "2025-05-06T12:00:00Z",
            "updated_at": "2025-05-06T12:00:00Z",
        }

    async def check_duplicate(self, task_id: str) -> bool:
        """Stub method to check if a task is a duplicate."""
        logger.info("STUB: Checking duplicate task", task_id=task_id)
        return False

    async def update_task_status(self, task_id: str, status: str, error: str = None) -> None:
        """Stub method to update task status."""
        logger.info("STUB: Updating task status", task_id=task_id, status=status, error=error)

    async def store_task_result(self, task_id: str, status: str, result: Dict[str, Any]) -> None:
        """Stub method to store task result."""
        logger.info("STUB: Storing task result", task_id=task_id, status=status)
