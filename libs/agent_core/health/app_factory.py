"""Health check app factory for agent_core services.

Implements the three required endpoints as specified in HEALTH_CHECK_STANDARD.md:
1. /health - Detailed health status
2. /healthz - Simple health probe
3. /metrics - Prometheus metrics.
"""

import prometheus_client
import structlog
from fastapi import FastAPI, Response

from .dependency_tracker import DependencyTracker

logger = structlog.get_logger(__name__)
def create_health_app(service_name: str, version: str) -> FastAPI:
    """Create a FastAPI app for health checks compliant with the platform standard.

    Args:
        service_name: The name of the service
        version: The version of the service

    Returns:
        A FastAPI app with standardized health endpoints.
    """
    health_app = FastAPI(
        title=f"{service_name} Health",
        description=f"Health checks for {service_name}",
        version=version,
    )

    # Create dependency tracker
    dependency_tracker = DependencyTracker(service_name)

    # 1. /health - Detailed Health Status
    @health_app.get("/health")
    async def health_check() -> dict:
        """Detailed health check endpoint used by monitoring systems and
        dependencies"""
        service_deps = dependency_tracker.check_dependencies()
        overall_status = "error" if "error" in service_deps.values() else "ok"

        return {"status": overall_status, "version": version, "services": service_deps}

    # 2. /healthz - Simple Health Probe
    @health_app.get("/healthz")
    async def simple_health() -> dict:
        """Simple health check for container orchestration"""
        return {"status": "ok"}

    # 3. /metrics - Prometheus Metrics
    @health_app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint"""
        return Response(content=prometheus_client.generate_latest(), media_type="text/plain")

    # Legacy endpoints (maintain backward compatibility)
    @health_app.get("/")
    async def root_health_check() -> dict:
        """Basic health check endpoint (legacy)."""
        return {"status": "healthy", "service": service_name, "version": version}

    @health_app.get("/ready")
    async def readiness_check() -> dict:
        """Readiness check endpoint (legacy)."""
        return {"status": "ready"}

    @health_app.get("/live")
    async def liveness_check() -> dict:
        """Liveness check endpoint (legacy)."""
        return {"status": "alive"}

    # Attach utility methods to the app for dependency management
    health_app.register_dependency = dependency_tracker.register_dependency
    health_app.update_dependency_status = dependency_tracker.update_dependency_status

    logger.info("Created standardized health app", service=service_name, version=version)
    return health_app
