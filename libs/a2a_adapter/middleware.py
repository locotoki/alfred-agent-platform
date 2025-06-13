"""Stub implementation of middleware for A2A Adapter"""

from typing import Any, Callable, Dict, List

import redis
import structlog

logger = structlog.get_logger(__name__)
class PolicyMiddleware:
    """Stub implementation of PolicyMiddleware for social-intel container"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        logger.info("Initialized stub PolicyMiddleware")

    async def apply_policies(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Stub method to apply policies to an envelope"""
        logger.info("STUB: Applying policies to envelope")
        return envelope

    async def register_policy(
        self, name: str, policy_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Stub method to register a policy"""
        logger.info("STUB: Registering policy", name=name)

    async def remove_policy(self, name: str) -> None:
        """Stub method to remove a policy"""
        logger.info("STUB: Removing policy", name=name)

    async def get_policies(self) -> List[str]:
        """Stub method to get all policies"""
        logger.info("STUB: Getting all policies")
        return []
