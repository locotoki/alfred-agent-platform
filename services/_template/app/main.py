"""Template service with standardized health and metrics endpoints"""

import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, Response

# Initialize FastAPI app
app = FastAPI(
    title="Alfred Template Service",
    description="Template service for the Alfred Agent Platform",
    version="0.1.0",
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define service metadata
SERVICE_NAME = "template-service"
SERVICE_VERSION = "0.1.0"

# Standard health endpoints
@app.get("/health")
async def health() -> Dict[str, Any]:
    """Detailed health endpoint that returns comprehensive status.

    Used by monitoring systems to get detailed health information.
    """
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "dependencies": {
            "database": "connected",
            "redis": "connected",
        },
    }

@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    """Simple health probe endpoint.

    Used by container orchestrators like Kubernetes for liveness probes.
    """
    return {"status": "ok"}

@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    metrics_text = f"""# HELP service_health Service health status (1 = healthy, 0 = unhealthy)
# TYPE service_health gauge
service_health{{name="{SERVICE_NAME}",version="{SERVICE_VERSION}"}} 1

# HELP service_requests_total Total number of requests processed
# TYPE service_requests_total counter
service_requests_total{{service="{SERVICE_NAME}"}} 0

# HELP service_request_duration_seconds Request duration in seconds
# TYPE service_request_duration_seconds histogram
service_request_duration_seconds_bucket{{service="{SERVICE_NAME}",le="0.1"}} 0
service_request_duration_seconds_bucket{{service="{SERVICE_NAME}",le="0.5"}} 0
service_request_duration_seconds_bucket{{service="{SERVICE_NAME}",le="1.0"}} 0
service_request_duration_seconds_bucket{{service="{SERVICE_NAME}",le="2.0"}} 0
service_request_duration_seconds_bucket{{service="{SERVICE_NAME}",le="5.0"}} 0
service_request_duration_seconds_bucket{{service="{SERVICE_NAME}",le="+Inf"}} 0
service_request_duration_seconds_sum{{service="{SERVICE_NAME}"}} 0
service_request_duration_seconds_count{{service="{SERVICE_NAME}"}} 0
"""
    return Response(content=metrics_text, media_type="text/plain")

# Main service endpoints
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint that returns basic service information"""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "description": "Template service for the Alfred Agent Platform",
    }

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
