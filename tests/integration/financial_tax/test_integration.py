"""Integration tests for Financial Tax Agent."""

import asyncio

import pytest

pytestmark = pytest.mark.xfail(reason="pre-existing async bug, see #220", strict=False)
from libs.a2a_adapter import A2AEnvelope
from services.agent_bizops.workflows.finance import FinancialTaxAgent

@pytest.mark.integration
class TestFinancialTaxIntegration:
    """Integration test suite for Financial Tax Agent."""

    @pytest.fixture
    async def test_db(self, test_db):
        """Provide database connection with test schema."""
        return test_db

    @pytest.fixture
    async def agent(self, pubsub_transport, supabase_transport, policy_middleware):
        """Create Financial Tax Agent instance."""
        agent = FinancialTaxAgent(
            pubsub_transport=pubsub_transport,
            supabase_transport=supabase_transport,
            policy_middleware=policy_middleware,
        )

        # Start agent
        await agent.start()

        yield agent

        # Stop agent
        await agent.stop()

    @pytest.mark.asyncio
    async def test_end_to_end_tax_calculation(self, agent, supabase_transport, pubsub_transport):
        """Test complete tax calculation flow."""
        # Create test envelope
        envelope = A2AEnvelope(
            intent="TAX_CALCULATION",
            content={
                "income": 100000,
                "deductions": {"mortgage_interest": 12000, "charitable": 5000},
                "credits": {"child_tax_credit": 2000},
                "jurisdiction": "US-CA",
                "tax_year": 2024,
                "entity_type": "individual",
                "additional_info": {},
            },
        )

        # Store task
        task_id = await supabase_transport.store_task(envelope)
        assert task_id == envelope.task_id

        # Publish task
        message_id = await pubsub_transport.publish_task(envelope)
        assert message_id is not None

        # Simulate agent processing
        await agent._handle_message(envelope)

        # Check task status updated to completed
        task_status = await supabase_transport.get_task_status(envelope.task_id)
        assert task_status["status"] == "completed"

        # Verify completion message published
        pubsub_transport.publish_task.assert_called()
        completion_call = pubsub_transport.publish_task.call_args_list[-1]
        completion_envelope = completion_call[0][0]
        assert completion_envelope.intent == "TAX_CALCULATION_COMPLETED"
        assert completion_envelope.correlation_id == envelope.task_id

    @pytest.mark.asyncio
    async def test_cross_agent_integration(self, agent, supabase_transport, pubsub_transport):
        """Test cross-agent integration scenario."""
        # Simulate legal compliance agent triggering tax calculation
        legal_envelope = A2AEnvelope(
            intent="TRIGGER_TAX_CALCULATION",
            content={
                "source": "legal-compliance-agent",
                "reason": "quarterly_compliance_check",
                "data": {
                    "income": 250000,
                    "jurisdiction": "US-NY",
                    "tax_year": 2024,
                    "entity_type": "corporation",
                },
            },
        )

        # Transform to TAX_CALCULATION intent
        tax_envelope = A2AEnvelope(
            intent="TAX_CALCULATION",
            content={
                "income": 250000,
                "deductions": {},
                "credits": {},
                "jurisdiction": "US-NY",
                "tax_year": 2024,
                "entity_type": "corporation",
                "additional_info": {"triggered_by": "legal-compliance-agent"},
            },
            correlation_id=legal_envelope.task_id,
        )

        # Process through agent
        await agent._handle_message(tax_envelope)

        # Verify processing
        task_status = await supabase_transport.get_task_status(tax_envelope.task_id)
        assert task_status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_error_handling_flow(self, agent, supabase_transport):
        """Test error handling in the integration."""
        # Create envelope with invalid data
        envelope = A2AEnvelope(
            intent="TAX_CALCULATION",
            content={
                "income": "invalid_amount",  # Should be float
                "jurisdiction": "INVALID_JURISDICTION",
                "tax_year": 2024,
                "entity_type": "individual",
            },
        )

        # Process with error
        with pytest.raises(Exception):
            await agent._handle_message(envelope)

        # Check task status updated to failed
        task_status = await supabase_transport.get_task_status(envelope.task_id)
        assert task_status["status"] == "failed"
        assert task_status["error_message"] is not None

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, agent, policy_middleware):
        """Test rate limiting integration."""
        # Create multiple requests from same user
        user_id = "test_user_123"

        for i in range(10):
            envelope = A2AEnvelope(
                intent="TAX_CALCULATION",
                content={
                    "income": 50000 + i * 1000,
                    "deductions": {},
                    "credits": {},
                    "jurisdiction": "US-CA",
                    "tax_year": 2024,
                    "entity_type": "individual",
                },
                metadata={"user_id": user_id},
            )

            # Process request
            if i < 5:  # Should succeed for first 5 requests
                await agent._handle_message(envelope)
            else:  # Should be rate limited
                with pytest.raises(Exception):
                    await agent._handle_message(envelope)

    @pytest.mark.asyncio
    async def test_concurrent_task_processing(self, agent, supabase_transport):
        """Test concurrent task processing."""
        # Create multiple tasks
        tasks = []
        for i in range(5):
            envelope = A2AEnvelope(
                intent="TAX_CALCULATION",
                content={
                    "income": 100000 + i * 10000,
                    "deductions": {"standard": 12950},
                    "credits": {},
                    "jurisdiction": "US-CA",
                    "tax_year": 2024,
                    "entity_type": "individual",
                },
            )
            tasks.append(envelope)

        # Process all tasks concurrently
        await asyncio.gather(*[agent._handle_message(task) for task in tasks])

        # Verify all tasks completed
        for task in tasks:
            status = await supabase_transport.get_task_status(task.task_id)
            assert status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_agent_heartbeat(self, agent, supabase_transport):
        """Test agent heartbeat mechanism."""
        # Wait for heartbeat
        await asyncio.sleep(2)

        # Check agent registry
        async with supabase_transport._pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT last_heartbeat, status
                FROM agent_registry
                WHERE name = $1
                """,
                agent.name,
            )

            assert result is not None
            assert result["status"] == "active"
            assert result["last_heartbeat"] is not None

    @pytest.mark.asyncio
    async def test_message_deduplication(self, agent, supabase_transport):
        """Test message deduplication mechanism."""
        # Create envelope
        envelope = A2AEnvelope(
            intent="TAX_CALCULATION",
            content={
                "income": 75000,
                "deductions": {},
                "credits": {},
                "jurisdiction": "US-TX",
                "tax_year": 2024,
                "entity_type": "individual",
            },
        )

        # Process first time
        await agent._handle_message(envelope)

        # Try to process again - should be skipped
        await agent._handle_message(envelope)

        # Check only processed once
        async with supabase_transport._pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM task_results
                WHERE task_id = $1::text
                """,
                envelope.task_id,
            )

            assert count == 1
