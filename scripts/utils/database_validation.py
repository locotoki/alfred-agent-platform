#!/usr/bin/env python3
"""Database validation script to ensure all required tables and indexes
exist.
"""

import asyncio
import os

import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)
REQUIRED_TABLES = [
    "tasks",
    "task_results",
    "processed_messages",
    "agent_registry",
    "embeddings",
]

REQUIRED_INDEXES = [
    "idx_tasks_status",
    "idx_tasks_created_at",
    "idx_tasks_intent",
    "idx_task_results_task_id",
    "idx_processed_messages_expires_at",
    "idx_agent_registry_status",
    "idx_embeddings_embedding",
]

REQUIRED_EXTENSIONS = [
    "uuid-ossp",
    "pgcrypto",
    "pgjwt",
    "pg_stat_statements",
    "pg_cron",
    "vector",
]

async def validate_database():
    """Validate database schema against requirements"""
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return False

    try:
        conn = await asyncpgconnect(database_url)  # type: ignore[unused-variable]
        # type: ignore[name-defined]
        # Check extensions
        extensions_query = """
        SELECT extname FROM pg_extension
        WHERE extname IN ($1, $2, $3, $4, $5, $6).
        """
        installed_extensions = await connfetch(extensions_query, *REQUIRED_EXTENSIONS)  # type: ignore[name-defined]
        installed_ext_names = {row["extname"] for row in installed_extensions}  # type: ignore[name-defined]

        missing_extensions = set(REQUIRED_EXTENSIONS) - installed_ext_names
        if missing_extensions:
            logger.warning("missing_extensions", missing=list(missing_extensions))

        # Check tables
        tables_query = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = ANY($1).
        """
        existing_tables = await connfetch(tables_query, REQUIRED_TABLES)  # type: ignore[name-defined]
        existing_table_names = {row["table_name"] for row in existing_tables}  # type: ignore[name-defined]

        missing_tables = set(REQUIRED_TABLES) - existing_table_names
        if missing_tables:
            logger.error("missing_tables", missing=list(missing_tables))
            return False

        # Check indexes
        indexes_query = """
        SELECT indexname FROM pg_indexes
        WHERE schemaname = 'public' AND indexname = ANY($1).
        """
        existing_indexes = await connfetch(indexes_query, REQUIRED_INDEXES)  # type: ignore[name-defined]
        existing_index_names = {row["indexname"] for row in existing_indexes}  # type: ignore[name-defined]

        missing_indexes = set(REQUIRED_INDEXES) - existing_index_names
        if missing_indexes:
            logger.warning("missing_indexes", missing=list(missing_indexes))

        # Check table schemas
        for table in REQUIRED_TABLES:
            columns_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position.
            """
            columns = await connfetch(columns_query, table)  # type: ignore[name-defined]
            # type: ignore[name-defined]
            logger.info(
                "table_schema",
                table=table,
                columns=[
                    {
                        "name": col["column_name"],
                        "type": col["data_type"],
                        "nullable": col["is_nullable"],
                    }
                    for col in columns
                ],
            )

        await connclose()  # type: ignore[name-defined]
        # type: ignore[name-defined]
        if missing_tables:
            return False

        logger.info("database_validation_complete", status="success")
        return True

    except Exception as e:
        logger.error("database_validation_failed", error=str(e))
        return False

if __name__ == "__main__":
    asyncio.run(validate_database())
