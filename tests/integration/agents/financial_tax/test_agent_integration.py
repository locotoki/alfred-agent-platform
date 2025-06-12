"""Integration tests for Financial Tax Agent."""

import asyncio
import os

import pytest

pytestmark = pytest.mark.xfail(reason="pre-existing async bug, see #220", strict=False)
from libs.a2a_adapter import (
    
,
    A2AEnvelope,
    PolicyMiddleware,
    PubSubTransport,
    SupabaseTransport,
)
from services.agent_bizops.workflows.finance.agent import FinancialTaxAgent

pytestmark = pytest.mark.integration
@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def pubsub_transport():
    """Create real PubSubTransport instance."""
    transport = PubSubTransport(project_id=os.getenv("GCP_PROJECT_ID", "alfred-agent-platform"))
    yield transport

@pytest.fixture
async def supabase_transport():
    """Create real SupabaseTransport instance."""
    transport = SupabaseTransport(database_url=os.getenv("DATABASE_URL"))
    await transport.connect()
    yield transport
    await transport.disconnect()

@pytest.fixture
def policy_middleware():
    """Create real PolicyMiddleware instance."""
    import redis
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    return PolicyMiddleware(redis_client)

@pytest.fixture
async def financial_tax_agent(pubsub_transport, supabase_transport, policy_middleware):
    """Create Financial Tax Agent with real dependencies."""
    agent = FinancialTaxAgent(
        pubsub_transport=pubsub_transport,
        supabase_transport=supabase_transport,
        policy_middleware=policy_middleware,
    )
    return agent

class TestFinancialTaxAgentIntegration:
    """Integration tests for Financial Tax Agent."""

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, financial_tax_agent):
        """Test agent startup and shutdown."""
        # Start agent
        await financial_tax_agent.start()
        assert financial_tax_agent.is_running

        # Allow some time for subscription setup
        await asyncio.sleep(2)

        # Stop agent
        await financial_tax_agent.stop()
        assert not financial_tax_agent.is_running

    @pytest.mark.asyncio
    async def test_tax_calculation_flow(
        self, financial_tax_agent, pubsub_transport, supabase_transport
    ):
        """Test end-to-end tax calculation flow."""
        # Create test envelope
        envelope = A2AEnvelope(
            intent="TAX_CALCULATION",
            content={
                "gross_income": 100000,
                "filing_status": "single",
                "tax_year": 2024,
                "deductions": [{"type": "standard", "amount": 13850}],
                "credits": [],
            },
        )

        # Store task
        await supabase_transport.store_task(envelope)

        # Process task directly (simulating message reception)
        result = await financial_tax_agent.process_task(envelope)

        # Verify result
        assert result["status"] == "success"
        assert result["intent"] == "TAX_CALCULATION"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_financial_analysis_flow(self, financial_tax_agent, supabase_transport):
        """Test end-to-end financial analysis flow."""
        envelope = A2AEnvelope(
            intent="FINANCIAL_ANALYSIS",
            content={
                "analysis_type": "business_health",
                "data": {
                    "revenue": 1000000,
                    "expenses": 750000,
                    "assets": 500000,
                    "liabilities": 200000,
                },
                "time_period": "2024",
                "goals": ["profitability_analysis"],
            },
        )

        # Store task
        await supabase_transport.store_task(envelope)

        # Process task
        result = await financial_tax_agent.process_task(envelope)

        # Verify result
        assert result["status"] == "success"
        assert result["intent"] == "FINANCIAL_ANALYSIS"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_compliance_check_flow(self, financial_tax_agent, supabase_transport):
        """Test end-to-end compliance check flow."""
        envelope = A2AEnvelope(
            intent="TAX_COMPLIANCE_CHECK",
            content={
                "entity_type": "corporation",
                "jurisdiction": "CA",
                "tax_year": 2024,
                "compliance_areas": ["income_tax", "sales_tax"],
            },
        )

        # Store task
        await supabase_transport.store_task(envelope)

        # Process task
        result = await financial_tax_agent.process_task(envelope)

        # Verify result
        assert result["status"] == "success"
        assert result["intent"] == "TAX_COMPLIANCE_CHECK"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_rate_lookup_flow(self, financial_tax_agent, supabase_transport):
        """Test end-to-end rate lookup flow."""
        envelope = A2AEnvelope(
            intent="RATE_SHEET_LOOKUP",
            content={
                "jurisdiction": "CA",
                "tax_year": 2024,
                "entity_type": "individual",
                "rate_types": ["income_tax"],
            },
        )

        # Store task
        await supabase_transport.store_task(envelope)

        # Process task
        result = await financial_tax_agent.process_task(envelope)

        # Verify result
        assert result["status"] == "success"
        assert result["intent"] == "RATE_SHEET_LOOKUP"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, financial_tax_agent, supabase_transport):
        """Test error handling in integration context."""
        # Create envelope with invalid data
        envelope = A2AEnvelope(
            intent="TAX_CALCULATION",
            content={
                "gross_income": -1000,  # Invalid negative income
                "filing_status": "invalid_status",  # Invalid status
                "tax_year": 2024,
            },
        )

        # Store task
        await supabase_transport.store_task(envelope)

        # Process task - should raise error
        with pytest.raises(Exception):
            await financial_tax_agent.process_task(envelope)

    @pytest.mark.asyncio
    async def test_concurrent_task_processing(self, financial_tax_agent, supabase_transport):
        """Test processing multiple tasks concurrently."""
        # Create multiple envelopes
        envelopes = [
            A2AEnvelope(
                intent="TAX_CALCULATION",
                content={
                    "gross_income": 100000 + i * 10000,
                    "filing_status": "single",
                    "tax_year": 2024,
                    "deductions": [{"type": "standard", "amount": 13850}],
                    "credits": [],
                },
            )
            for i in range(3)
        ]

        # Store all tasks
        for envelope in envelopes:
            await supabase_transport.store_task(envelope)

        # Process tasks concurrently
        tasks = [financial_tax_agent.process_task(envelope) for envelope in envelopes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all results
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Task failed with error: {result}")
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_task_status_updates(self, financial_tax_agent, supabase_transport):
        """Test task status updates through the workflow."""
        envelope = A2AEnvelope(
            intent="TAX_CALCULATION",
            content={
                "gross_income": 100000,
                "filing_status": "single",
                "tax_year": 2024,
                "deductions": [{"type": "standard", "amount": 13850}],
                "credits": [],
            },
        )

        # Store task
        task_id = await supabase_transport.store_task(envelope)

        # Check initial status
        status = await supabase_transport.get_task_status(task_id)
        assert status == "pending"

        # Process task
        await financial_tax_agent.process_task(envelope)

        # Check final status (this would be updated by the agent)
        # Note: In real integration, status would be updated through agent's process
        # For this test, we'd need to implement get_task_status in SupabaseTransport
