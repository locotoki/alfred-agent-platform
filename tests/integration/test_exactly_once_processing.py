import asyncio
import os
from datetime import datetime, timedelta

import pytest

from libs.a2a_adapter import SupabaseTransport

@pytest.mark.integration
class TestExactlyOnceProcessing:
    @pytest.fixture
    async def supabase_transport(self):
        """Create a test SupabaseTransport instance."""
        transport = SupabaseTransport(database_url=os.getenv("DATABASE_URL"))
        await transport.connect()
        yield transport
        await transport.disconnect()

    @pytest.fixture
    async def cleanup_test_data(self, supabase_transport):
        """Clean up test data before and after tests."""
        # Clean before test
        async with supabase_transport._pool.acquire() as conn:
            await conn.execute("DELETE FROM processed_messages WHERE message_id LIKE 'test_%'")

        yield

        # Clean after test
        async with supabase_transport._pool.acquire() as conn:
            await conn.execute("DELETE FROM processed_messages WHERE message_id LIKE 'test_%'")

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, supabase_transport, cleanup_test_data):
        """Test that duplicate messages are properly detected."""
        message_id = "test_duplicate_123"

        # First check should return False (not duplicate)
        is_duplicate1 = await supabase_transport.check_duplicate(message_id)
        assert is_duplicate1 is False

        # Second check should return True (is duplicate)
        is_duplicate2 = await supabase_transport.check_duplicate(message_id)
        assert is_duplicate2 is True

        # Verify the message is in the database
        async with supabase_transport._pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM processed_messages WHERE message_id = $1",
                message_id,
            )
            assert result == 1

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_checks(self, supabase_transport, cleanup_test_data):
        """Test duplicate detection under concurrent access."""
        message_id = "test_concurrent_456"

        # Run multiple concurrent checks
        tasks = []
        for _ in range(10):
            tasks.append(supabase_transport.check_duplicate(message_id))

        results = await asyncio.gather(*tasks)

        # Only one check should return False (not duplicate)
        false_count = sum(1 for r in results if r is False)
        true_count = sum(1 for r in results if r is True)

        assert false_count == 1
        assert true_count == 9

    @pytest.mark.asyncio
    async def test_cleanup_expired_messages(self, supabase_transport, cleanup_test_data):
        """Test cleanup of expired messages."""
        async with supabase_transport._pool.acquire() as conn:
            # Insert an expired message
            await conn.execute(
                """
                INSERT INTO processed_messages (message_id, processed_at, expires_at)
                VALUES ($1, $2, $3)
                """,
                "test_expired_789",
                datetime.utcnow() - timedelta(hours=49),
                datetime.utcnow() - timedelta(hours=1),
            )

            # Insert a non-expired message
            await conn.execute(
                """
                INSERT INTO processed_messages (message_id)
                VALUES ($1)
                """,
                "test_valid_101112",
            )

            # Run cleanup
            await supabase_transport.cleanup_processed_messages()

            # Verify expired message is gone
            expired_count = await conn.fetchval(
                "SELECT COUNT(*) FROM processed_messages WHERE message_id = $1",
                "test_expired_789",
            )
            assert expired_count == 0

            # Verify valid message still exists
            valid_count = await conn.fetchval(
                "SELECT COUNT(*) FROM processed_messages WHERE message_id = $1",
                "test_valid_101112",
            )
            assert valid_count == 1

    @pytest.mark.asyncio
    async def test_message_expiration_timing(self, supabase_transport, cleanup_test_data):
        """Test that messages have correct expiration times."""
        message_id = "test_expiration_131415"

        await supabase_transport.check_duplicate(message_id)

        async with supabase_transport._pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT processed_at, expires_at
                FROM processed_messages
                WHERE message_id = $1
                """,
                message_id,
            )

            # Verify expiration is 48 hours after processing
            time_diff = result["expires_at"] - result["processed_at"]
            hours_diff = time_diff.total_seconds() / 3600

            assert 47.9 <= hours_diff <= 48.1  # Allow small variance
