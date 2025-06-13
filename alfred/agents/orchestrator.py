"""Orchestrator for Agent coordination.

This module contains the AgentOrchestrator class which coordinates
interactions between different agent types based on intent.
"""

import uuid
from typing import Any, Callable, Dict, Optional

import structlog
from prometheus_client import Counter

from .intent_router import Intent, IntentRouter

# Create a default router instance
router = IntentRouter()
# Register common patterns
router.register_pattern("help", r"(?:can you )?(?:help|assist) (?:me )?(?:with )?(?P<topic>.+)")
router.register_pattern("summarize", r"(?:can you )?summarize (?P<text>.+)")

# Prometheus metrics
route_total = Counter("alfred_orchestrator_route_total", "Total routes processed", ["intent_type"])

logger = structlog.get_logger(__name__)


class AgentOrchestrator:
    """Coordinate agent interactions through intent-based routing."""

    def __init__(self) -> None:
        """Initialize orchestrator with the default intent router."""
        self._intent_router = router

    async def process_message(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a message through the orchestrator.

        Args:
            message: The incoming message to process
            context: Optional context information

        Returns:
            dict: A response containing the processed result
        """
        if context is None:
            context = {}

        # Generate a request ID if not provided
        request_id = context.get("request_id", str(uuid.uuid4()))

        # Add request ID to logger context
        log = logger.bind(request_id=request_id)
        log.info("processing_message", message_length=len(message))

        # Route to determine intent
        intent = self._intent_router.route(message)

        # Increment the metric for the intent type
        route_total.labels(intent_type=intent.type).inc()

        # Log the detected intent
        log.info("intent_detected", intent_type=intent.type, confidence=intent.confidence)

        # Process based on intent
        response = await self._process_intent(intent, context)

        # Add metadata to response
        response["request_id"] = request_id
        response["intent"] = intent.type
        response["confidence"] = intent.confidence

        return response

    async def _process_intent(self, intent: Intent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process an intent through the appropriate agent.

        Args:
            intent: The classified intent
            context: Context information

        Returns:
            dict: The processed response
        """
        # This is where we'd dispatch to different agents based on intent
        # For now, use the default handlers from the router
        text_response = self._intent_router.handle(intent, context=context)

        # For some intents, we might want to process asynchronously
        # through other agents - here we could call those agents

        return {
            "text": text_response or "I'm still learning how to respond to that.",
            "processed": True,
            "agent": "default",
        }

    def register_agent_handler(self, intent_type: str, handler_fn: Callable[..., Any]) -> None:
        """Register an agent handler for a specific intent type.

        Args:
            intent_type: The intent type to handle
            handler_fn: The handler function
        """
        self._intent_router.register_handler(intent_type, handler_fn)
        logger.info("agent_handler_registered", intent_type=intent_type)

    def register_intent_pattern(self, intent_type: str, pattern: str) -> None:
        """Register a regex pattern for intent detection.

        Args:
            intent_type: The intent type to match
            pattern: The regex pattern
        """
        self._intent_router.register_pattern(intent_type, pattern)
        logger.info("intent_pattern_registered", intent_type=intent_type)
