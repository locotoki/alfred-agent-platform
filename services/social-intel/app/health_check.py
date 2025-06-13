"""Enhanced health check implementation for the Social Intelligence service"""

# type: ignore
import asyncio
import os
import time

import aiohttp
import structlog
from fastapi import APIRouter, Response, status

from app.database import get_pool
from app.metrics import OFFLINE_MODE_GAUGE
from app.utils.circuit_breaker import CircuitBreaker

logger = structlog.get_logger(__name__)
# Create a router for health check endpoints
health_router = APIRouter(tags=["health"])

# Initialize circuit breakers for external dependencies
db_circuit = CircuitBreaker(name="database", failure_threshold=3, reset_timeout=30.0)
youtube_circuit = CircuitBreaker(name="youtube_api", failure_threshold=3, reset_timeout=120.0)

# Global health state
health_state = {
    "status": "initializing",
    "components": {
        "database": {"status": "unknown"},
        "youtube_api": {"status": "unknown"},
    },
    "last_check": time.time(),
    "is_offline_mode": False,
}


@health_router.get("/health")
async def basic_health():
    """Basic health check endpoint"""
    global health_state

    # Determine overall status
    if health_state["status"] == "unhealthy":
        return Response(
            content="Service Unhealthy", status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    else:
        return {"status": health_state["status"]}


@health_router.get("/health/detailed")
async def detailed_health():
    """Detailed health check including component status"""
    global health_state

    # Add current time
    health_state["last_check"] = time.time()

    # Return full health state
    return health_state


@health_router.get("/healthz")
async def simple_health():
    """Simple health check for container probes"""
    global health_state
    if health_state["status"] == "unhealthy":
        return Response(
            content='{"status":"error"}', media_type="application/json", status_code=503
        )
    return {"status": "ok"}


@health_router.post("/health/check-now")
async def trigger_health_check():
    """Manually trigger a full health check"""
    await check_all_dependencies()
    return health_state


async def check_all_dependencies():
    """Check all external dependencies and update health state"""
    global health_state

    # Check database
    db_healthy = await check_database()

    # Check YouTube API
    youtube_healthy = await check_youtube_api()

    # Update overall status
    if not db_healthy:
        health_state["status"] = "unhealthy"
        health_state["is_offline_mode"] = True
    elif not youtube_healthy:
        health_state["status"] = "degraded"
        health_state["is_offline_mode"] = True
    else:
        health_state["status"] = "healthy"
        health_state["is_offline_mode"] = False

    # Update metrics
    OFFLINE_MODE_GAUGE.set(1 if health_state["is_offline_mode"] else 0)

    return health_state


async def check_database() -> bool:
    """Check database connectivity.

    Returns:
        True if database is healthy, False otherwise.
    """
    global health_state

    try:
        # Use circuit breaker for database checks
        await db_circuitexecute(async_check_db_connection)

        # Update health state
        health_state["components"]["database"] = {
            "status": "healthy",
            "last_check": time.time(),
        }

        logger.info("database_health_check_success")
        return True
    except Exception as e:
        # Update health state
        health_state["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "last_check": time.time(),
        }

        logger.error("database_health_check_failed", error=str(e))
        return False


async def async_check_db_connection():
    """Execute a simple database query to check connectivity"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Try to execute a simple query
        await connfetchval("SELECT 1")


async def check_youtube_api() -> bool:
    """Check YouTube API connectivity.

    Returns:
        True if YouTube API is accessible, False otherwise.
    """
    global health_state

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        health_state["components"]["youtube_api"] = {
            "status": "unhealthy",
            "error": "YouTube API key not configured",
            "last_check": time.time(),
        }
        return False

    try:
        # Use circuit breaker for YouTube API checks
        await youtube_circuitexecute(async_check_youtube_api, api_key)

        # Update health state
        health_state["components"]["youtube_api"] = {
            "status": "healthy",
            "last_check": time.time(),
        }

        logger.info("youtube_api_health_check_success")
        return True
    except Exception as e:
        # Update health state
        health_state["components"]["youtube_api"] = {
            "status": "unhealthy",
            "error": str(e),
            "last_check": time.time(),
        }

        logger.error("youtube_api_health_check_failed", error=str(e))
        return False


async def async_check_youtube_api(api_key: str):
    """Make a simple API call to check YouTube API connectivity"""
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "chart": "mostPopular",
        "maxResults": 1,
        "key": api_key,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                text = await responsetext()
                raise Exception(f"YouTube API returned status {response.status}: {text}")

            # Parse response to verify it's valid
            data = await responsejson()
            if "items" not in data:
                raise Exception("Invalid YouTube API response format")


async def start_health_check_scheduler():
    """Start periodic health checks"""
    logger.info("Starting health check scheduler")

    # Run initial health check
    await check_all_dependencies()

    # Schedule periodic checks
    while True:
        try:
            await asynciosleep(60)  # Check every minute
            await check_all_dependencies()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Health check scheduler error", error=str(e))
            await asynciosleep(10)  # Wait a bit before retrying
