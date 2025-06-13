#!/usr/bin/env python3
"""Redis Health Check Wrapper for the Alfred Agent Platform.

This script provides standardized health check endpoints for Redis:
1. /health - Detailed health status
2. /healthz - Simple health probe
3. /metrics - Prometheus metrics

It acts as a wrapper around Redis to make it compliant with the platform
health check standard.
"""

import os
import time
from typing import Dict

import prometheus_client
import redis
from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Gauge

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SERVICE_NAME = "redis"
VERSION = "7.0.0"  # Redis version

# Create FastAPI app
app = FastAPI(
    title=f"{SERVICE_NAME} Health",
    description=f"Health checks for {SERVICE_NAME}",
    version=VERSION,
)

# Prometheus metrics
redis_up = Gauge("redis_up", "Redis availability")
redis_commands_total = Counter("redis_commands_total", "Total Redis commands processed")
redis_connections = Gauge("redis_connections", "Current Redis connections")
redis_memory_used_bytes = Gauge("redis_memory_used_bytes", "Redis memory usage in bytes")
redis_last_check_time = Gauge("redis_last_check_time", "Timestamp of last Redis health check")

# Redis client
redis_client = redis.from_url(REDIS_URL)

def check_redis_health() -> Dict[str, str]:
    """Check Redis connection and status.

    Returns:
        Dictionary with Redis health status.
    """
    try:
        # Try to ping Redis
        response = redis_client.ping()
        if response:
            redis_up.set(1)

            # Get Redis info for metrics
            info = redis_client.info()
            redis_connections.set(info.get("connected_clients", 0))
            redis_memory_used_bytes.set(info.get("used_memory", 0))
            redis_commands_total.inc()

            return {"status": "ok"}
        else:
            redis_up.set(0)
            return {"status": "error", "error": "Redis ping failed"}
    except redis.exceptions.ConnectionError as e:
        redis_up.set(0)
        return {"status": "error", "error": str(e)}
    except Exception as e:
        redis_up.set(0)
        return {"status": "error", "error": str(e)}
    finally:
        redis_last_check_time.set(time.time())

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    result = check_redis_health()

    if result["status"] == "error":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_200_OK

    return {
        "status": result["status"],
        "version": VERSION,
        "services": {"redis": result["status"]},
    }, status_code

@app.get("/healthz")
async def simple_health():
    """Simple health check for container probes"""
    result = check_redis_health()

    if result["status"] == "error":
        return Response(
            content='{"status":"error"}',
            media_type="application/json",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    else:
        return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=prometheus_client.generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9091)
