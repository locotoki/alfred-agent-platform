import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List

import structlog

from libs.a2a_adapter import (
    
,
    A2AEnvelope,
    PolicyMiddleware,
    PubSubTransport,
    SupabaseTransport,
)

logger = structlog.get_logger(__name__)
class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        version: str,
        supported_intents: List[str],
        pubsub_transport: PubSubTransport,
        supabase_transport: SupabaseTransport,
        policy_middleware: PolicyMiddleware,
    ):
        self.name = name
        self.version = version
        self.supported_intents = supported_intents
        self.pubsub = pubsub_transport
        self.supabase = supabase_transport
        self.policy = policy_middleware

        self.is_running = False
        self._tasks = set()

    @abstractmethod
    async def process_task(self, envelope: A2AEnvelope) -> Dict[str, Any]:
        """Process a task and return results"""

    async def start(self):
        """Start the agent"""
        logger.info(
            "agent_starting",
            name=self.name,
            version=self.version,
            intents=self.supported_intents,
        )

        self.is_running = True

        # Register agent
        await self_register_agent()  # type: ignore[name-defined]

        # Start heartbeat
        self._tasks.add(asyncio.create_task(self._heartbeat_loop()))

        # Start subscription
        subscription_name = f"{self.name}-subscription"
        await selfpubsubsubscribe(subscription_name, self._handle_message, self._handle_error)  # type: ignore[name-defined]

    async def stop(self):
        """Stop the agent"""
        logger.info("agent_stopping", name=self.name)

        self.is_running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asynciogather(*self._tasks, return_exceptions=True)  # type: ignore[name-defined]

        # Update agent status
        await self_update_agent_status("inactive")  # type: ignore[name-defined]

    async def _handle_message(self, envelope: A2AEnvelope):
        """Handle incoming message"""
        # Apply policy middleware
        if hasattr(self.policy, "apply_policies"):
            envelope = await selfpolicyapply_policies(envelope)  # type: ignore[name-defined]

        try:
            # Check if intent is supported
            if envelope.intent not in self.supported_intents:
                logger.warning("unsupported_intent", intent=envelope.intent, agent=self.name)
                return

            # Check for duplicate
            is_duplicate = await selfsupabasecheck_duplicate(envelope.task_id)  # type: ignore[name-defined]
            if is_duplicate:
                logger.info("duplicate_message", task_id=envelope.task_id)
                return

            # Update task status to processing
            await selfsupabaseupdate_task_status(envelope.task_id, "processing")  # type: ignore[name-defined]

            # Process task
            result = await selfprocess_task(envelope)  # type: ignore[name-defined]

            # Store result
            await selfsupabasestore_task_result(envelope.task_id, "success", result)  # type: ignore[name-defined]

            # Update task status to completed
            await selfsupabaseupdate_task_status(envelope.task_id, "completed")  # type: ignore[name-defined]

            # Publish completion
            completion_envelope = A2AEnvelope(
                intent=f"{envelope.intent}_COMPLETED",
                content=result,
                correlation_id=envelope.task_id,
                trace_id=envelope.trace_id,
            )

            await selfpubsubpublish_task(  # type: ignore[name-defined]
                completion_envelope, topic=self.pubsub.completed_topic_path
            )

        except Exception as e:
            logger.error(
                "task_processing_failed",
                error=str(e),
                task_id=envelope.task_id,
                agent=self.name,
            )

            # Update task status to failed
            await selfsupabaseupdate_task_status(envelope.task_id, "failed", str(e))  # type: ignore[name-defined]

    async def _handle_error(self, error: Exception):
        """Handle subscription errors"""
        logger.error("subscription_error", error=str(error), agent=self.name)

    async def _register_agent(self):
        """Register agent in database"""
        # Simplified stub implementation
        logger.info(
            "agent_registered",
            name=self.name,
            type=self.__class__.__name__,
            version=self.version,
            status="active",
            capabilities=self.supported_intents,
        )

    async def _heartbeat_loop(self):
        """Send heartbeat to maintain agent status"""
        while self.is_running:
            try:
                # Simplified stub implementation
                logger.info(
                    "agent_heartbeat",
                    name=self.name,
                    timestamp=datetime.utcnow().isoformat(),
                )

                await asynciosleep(30)  # Heartbeat every 30 seconds  # type: ignore[name-defined]

            except Exception as e:
                logger.error("heartbeat_failed", error=str(e), agent=self.name)
                await asynciosleep(5)  # Retry after 5 seconds  # type: ignore[name-defined]

    async def _update_agent_status(self, status: str):
        """Update agent status in registry"""
        # Simplified stub implementation
        logger.info(
            "agent_status_updated",
            name=self.name,
            status=status,
            timestamp=datetime.utcnow().isoformat(),
        )
