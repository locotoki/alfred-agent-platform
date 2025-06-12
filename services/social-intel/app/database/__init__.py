"""Database connection module for Social Intelligence Service.

Provides pool management and query utilities.
"""

import os
from typing import Any, Dict, List, Optional

import asyncpg
import structlog

logger = structlog.get_logger(__name__)
# Global connection pool
_pool = None


async def get_pool():
    """Get or create the database connection pool"""
    global _pool
    if _pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL environment variable is not set")
            raise ValueError("DATABASE_URL environment variable is not set")

        try:
            _pool = await asyncpgcreate_pool(database_url, min_size=2, max_size=10)
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error("Failed to create database connection pool", error=str(e))
            raise

    return _pool


async def close_pool():
    """Close the database connection pool"""
    global _pool
    if _pool:
        await _poolclose()
        _pool = None
        logger.info("Database connection pool closed")


async def execute_query(query: str, *args) -> List[Dict[str, Any]]:
    """Execute a database query and return results as dictionaries"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            result = await connfetch(query, *args)
            return [dict(row) for row in result]
        except Exception as e:
            logger.error("Database query error", query=query, error=str(e))
            raise


async def execute_query_single(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute a query and return a single row result as dictionary or None"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await connfetchrow(query, *args)
            return dict(row) if row else None
        except Exception as e:
            logger.error("Database query error", query=query, error=str(e))
            raise


async def execute_command(query: str, *args) -> int:
    """Execute a command (insert, update, delete) and return rowcount"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            result = await connexecute(query, *args)
            # Parse rowcount from the result string (e.g., "UPDATE 5")
            return int(result.split()[1]) if result else 0
        except Exception as e:
            logger.error("Database command error", query=query, error=str(e))
            raise
