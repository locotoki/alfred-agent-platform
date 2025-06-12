"""HTTP server for Slack Adapter service"""

import os

import structlog
import uvicorn
from fastapi import FastAPI
from prometheus_client import Counter

app = FastAPI(title="Slack Adapter Service")
logger = structlog.get_logger(__name__)

# Metrics
request_counter = Counter("slack_adapter_requests_total", "Total number of requests", ["endpoint"])

@app.get("/health")
async def health_check():
    """Health check endpoint for the service"""
    request_counter.labels(endpoint="health").inc()
    return {"status": "ok", "service": "slack-adapter"}

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for the service"""
    request_counter.labels(endpoint="ready").inc()
    return {"status": "ready", "service": "slack-adapter"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    logger.info("Starting Slack Adapter service", port=port)
    uvicorn.run(app, host="0.0.0.0", port=port)
