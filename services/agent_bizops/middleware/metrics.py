"""Prometheus metrics middleware for Agent BizOps."""

import time

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Summary, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

class PrometheusMetrics:
    """Prometheus metrics collector for BizOps workflows."""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern to avoid duplicate metric registration."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Prometheus metrics."""
        if self._initialized:
            return

        # Request counters by workflow
        self.request_total = Counter(
            "bizops_request_total",
            "Total number of requests",
            labelnames=["method", "endpoint", "status_code", "bizops_workflow"],
        )

        # Request duration histogram
        self.request_duration = Histogram(
            "bizops_request_duration_seconds",
            "Request duration in seconds",
            labelnames=["method", "endpoint", "bizops_workflow"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        # Request duration summary for percentiles
        self.request_duration_summary = Summary(
            "bizops_request_duration_summary_seconds",
            "Request duration summary in seconds",
            labelnames=["method", "endpoint", "bizops_workflow"],
        )

        # Request failures counter
        self.request_failures = Counter(
            "bizops_request_failures_total",
            "Total number of failed requests",
            labelnames=["method", "endpoint", "bizops_workflow", "error_type"],
        )

        # Active requests gauge
        self.active_requests = Counter(
            "bizops_active_requests",
            "Number of requests currently being processed",
            labelnames=["bizops_workflow"],
        )

        # Workflow-specific business metrics
        self.workflow_operations = Counter(
            "bizops_workflow_operations_total",
            "Total workflow operations by type",
            labelnames=["bizops_workflow", "operation_type", "status"],
        )

        # Mark as initialized
        self._initialized = True

    def get_workflow_from_path(self, path: str) -> str:
        """Determine workflow from request path."""
        if "/legal/" in path or "/compliance/" in path:
            return "legal"
        elif "/finance/" in path or "/tax/" in path:
            return "finance"
        elif "/health" in path:
            return "system"
        else:
            return "unknown"

    def get_operation_type(self, path: str, method: str) -> str:
        """Determine operation type from request."""
        if "/health" in path:
            return "health_check"
        elif "/legal/compliance" in path:
            return "compliance_check"
        elif "/legal/contract" in path:
            return "contract_review"
        elif "/finance/calculation" in path:
            return "tax_calculation"
        elif "/finance/analysis" in path:
            return "financial_analysis"
        else:
            return f"{method.lower()}_request"

    def record_request_metrics(self, request: Request, response: Response, duration: float):
        """Record metrics for a completed request."""
        method = request.method
        path = request.url.path
        status_code = str(response.status_code)
        workflow = self.get_workflow_from_path(path)
        operation_type = self.get_operation_type(path, method)

        # Record basic request metrics
        self.request_total.labels(
            method=method, endpoint=path, status_code=status_code, bizops_workflow=workflow
        ).inc()

        # Record duration metrics
        self.request_duration.labels(
            method=method, endpoint=path, bizops_workflow=workflow
        ).observe(duration)

        self.request_duration_summary.labels(
            method=method, endpoint=path, bizops_workflow=workflow
        ).observe(duration)

        # Record failures for 4xx/5xx status codes
        if response.status_code >= 400:
            error_type = "client_error" if response.status_code < 500 else "server_error"
            self.request_failures.labels(
                method=method, endpoint=path, bizops_workflow=workflow, error_type=error_type
            ).inc()

        # Record workflow operation
        operation_status = "success" if response.status_code < 400 else "failure"
        self.workflow_operations.labels(
            bizops_workflow=workflow, operation_type=operation_type, status=operation_status
        ).inc()

# Global metrics instance
metrics = PrometheusMetrics()

class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for collecting Prometheus metrics."""

    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics."""
        # Handle metrics endpoint
        if request.url.path == "/metrics":
            return PlainTextResponse(
                generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8"
            )

        # Skip metrics for favicon and static assets
        if request.url.path in ["/favicon.ico", "/robots.txt"]:
            return await call_next(request)

        # Track active requests
        workflow = metrics.get_workflow_from_path(request.url.path)
        metrics.active_requests.labels(bizops_workflow=workflow).inc()

        start_time = time.time()

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Create error response
            response = Response(
                content=f"Internal Server Error: {str(e)}", status_code=500, media_type="text/plain"
            )
            return response
        finally:
            # Record metrics after request completion
            duration = time.time() - start_time

            # Ensure we have a valid response object
            if "response" in locals():
                metrics.record_request_metrics(request, response, duration)

            # Decrement active requests
            metrics.active_requests.labels(bizops_workflow=workflow)._value._value -= 1

def setup_metrics_middleware(app):
    """Set up Prometheus metrics middleware."""
    app.add_middleware(MetricsMiddleware)
