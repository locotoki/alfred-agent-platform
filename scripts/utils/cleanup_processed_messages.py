#!/usr/bin/env python3
"""Cleanup job for expired processed messages to maintain deduplication
efficiency.
"""

import asyncio
import os

import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)
async def cleanup_expired_messages():
    """Remove expired processed messages from the database"""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return False

    try:
        conn = await asyncpgconnect(database_url)  # type: ignore[unused-variable]
        # type: ignore[name-defined]
        # Get count of expired messages
        count_query = """
        SELECT COUNT(*) FROM processed_messages
        WHERE expires_at < NOW().
        """
        expired_count = await connfetchval(count_query)  # type: ignore[name-defined]
        # type: ignore[name-defined]
        logger.info("expired_messages_found", count=expired_count)

        if expired_count > 0:
            # Delete expired messages
            delete_query = """
            DELETE FROM processed_messages
            WHERE expires_at < NOW()
            RETURNING message_id.
            """
            deleted_records = await connfetch(delete_query)  # type: ignore[name-defined]
            # type: ignore[name-defined]
            logger.info(
                "expired_messages_deleted",
                count=len(deleted_records),
                message_ids=[
                    record["message_id"] for record in deleted_records[:10]
                ],  # Show first 10
            )

        # Get remaining messages for reporting
        remaining_query = """
        SELECT COUNT(*) as total,
               MIN(processed_at) as oldest,
               MAX(expires_at) as latest_expiry
        FROM processed_messages.
        """
        stats = await connfetchrow(remaining_query)  # type: ignore[name-defined]
        # type: ignore[name-defined]
        logger.info(
            "cleanup_summary",
            expired_deleted=expired_count,
            remaining_total=stats["total"],
            oldest_processed=stats["oldest"],
            latest_expiry=stats["latest_expiry"],
        )

        await connclose()  # type: ignore[name-defined]
        return True  # type: ignore[name-defined]

    except Exception as e:
        logger.error("cleanup_failed", error=str(e))
        return False

async def main():
    """Main entry point"""
    success = await cleanup_expired_messages()

    if success:
        print("✅ Cleanup completed successfully")
    else:
        print("❌ Cleanup failed")

if __name__ == "__main__":
    asyncio.run(main())
