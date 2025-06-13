"""Agent BizOps Main Application."""

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ..middleware.metrics import setup_metrics_middleware

# Set up structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Agent BizOps",
    description="Business Operations Agent - handles legal and financial workflows",
    version="2.0.0",
)

# Setup Prometheus metrics middleware
setup_metrics_middleware(app)

# Static workflows configuration - no longer environment-driven
WORKFLOWS_ENABLED = ["finance", "legal"]

@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse(
        {"status": "healthy", "service": "agent-bizops", "workflows_enabled": WORKFLOWS_ENABLED}
    )

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Agent BizOps Service", "workflows_enabled": WORKFLOWS_ENABLED}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
