#!/usr/bin/env python3
"""PubSub Emulator Health Check Wrapper for the Alfred Agent Platform.

This script provides standardized health check endpoints for the PubSub emulator:
1. /health - Detailed health status
2. /healthz - Simple health probe
3. /metrics - Prometheus metrics

It acts as a wrapper around the PubSub emulator to make it compliant with the platform
health check standard.
"""
# type: ignore
import json
import os
import time
import urllib.request
from typing import Dict

import prometheus_client
from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Gauge

# Configuration
PUBSUB_HOST = os.environ.get("PUBSUB_HOST", "localhost:8085")
PROJECT_ID = os.environ.get("A
RED_PROJECT_ID", "alfred-agent-platform")
SERVICE_NAME = "pubsub-emulator"
VERSION = "1.0.0"

# Create FastAPI app
app = FastAPI(
    title=f"{SERVICE_NAME} Health",
    description=f"Health checks for {SERVICE_NAME}",
    version=VERSION,
)

# Prometheus metrics
pubsub_up = Gauge("pubsub_up", "PubSub emulator availability")
pubsub_requests_total = Counter("pubsub_requests_total", "Total PubSub requests processed")
pubsub_topics = Gauge("pubsub_topics", "Number of topics in PubSub")
pubsub_subscriptions = Gauge("pubsub_subscriptions", "Number of subscriptions in PubSub")
pubsub_last_check_time = Gauge("pubsub_last_check_time", "Timestamp of last PubSub health check")

def check_pubsub_health() -> Dict[str, str]:
    """Check PubSub emulator connection and status.

    Returns:
        Dictionary with PubSub health status.
    """
    try:
        # Try to list topics
        url = f"http://{PUBSUB_HOST}/v1/projects/{PROJECT_ID}/topics"
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                topics = json.loads(response.read().decode("utf-8"))

                # Set metrics
                pubsub_up.set(1)
                pubsub_requests_total.inc()
                if "topics" in topics:
                    pubsub_topics.set(len(topics["topics"]))

                # Get subscriptions
                sub_url = f"http://{PUBSUB_HOST}/v1/projects/{PROJECT_ID}/subscriptions"
                try:
                    with urllib.request.urlopen(sub_url, timeout=2) as sub_response:
                        if sub_response.status == 200:
                            subscriptions = json.loads(sub_response.read().decode("utf-8"))
                            if "subscriptions" in subscriptions:
                                pubsub_subscriptions.set(len(subscriptions["subscriptions"]))
                except Exception:
                    pass  # Ignore subscription check failures

                return {"status": "ok"}
            else:
                pubsub_up.set(0)
                return {
                    "status": "error",
                    "error": f"PubSub returned status {response.status}",
                }
    except Exception as e:
        pubsub_up.set(0)
        return {"status": "error", "error": str(e)}
    finally:
        pubsub_last_check_time.set(time.time())

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    result = check_pubsub_health()

    if result["status"] == "error":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_200_OK

    return {
        "status": result["status"],
        "version": VERSION,
        "services": {"pubsub": result["status"]},
    }, status_code

@app.get("/healthz")
async def simple_health():
    """Simple health check for container probes"""
    result = check_pubsub_health()

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
