"""OpenTelemetry tracing provider for observability"""

import os
from functools import wraps
from typing import Any, Dict, Optional

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

logger = structlog.get_logger(__name__)
class TracingProvider:
    """Provider for OpenTelemetry tracing functionality"""

    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        """Initialize the tracing provider with service information.

        Args:
            service_name: Name of the service for tracing
            service_version: Version of the service, defaults to 1.0.0.
        """
        self.service_name = service_name
        self.service_version = service_version
        self.tracer = self._setup_tracing()

    def _setup_tracing(self) -> trace.Tracer:
        """Set up OpenTelemetry tracing"""
        resource = Resource(
            attributes={
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
            }
        )

        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            insecure=True,
        )

        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)

        trace.set_tracer_provider(provider)

        return trace.get_tracer(self.service_name)

    def trace_function(self, span_name: Optional[str] = None):
        """Create a decorator to trace function execution.

        Apply to functions to automatically create spans for OpenTelemetry tracing.

        Args:
            span_name: Optional custom name for the span. Defaults to function name.

        Returns:
            A decorator function for tracing.
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                name = span_name or f"{func.__module__}.{func.__name__}"

                with self.tracer.start_as_current_span(name) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise

            return wrapper

        return decorator

    def get_current_span(self) -> trace.Span:
        """Get the current active span"""
        return trace.get_current_span()

    def add_span_attributes(self, attributes: Dict[str, Any]):
        """Add attributes to the current span"""
        span = self.get_current_span()
        if span and span.is_recording():
            for key, value in attributes.items():
                span.set_attribute(key, value)

    def add_span_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the current span"""
        span = self.get_current_span()
        if span and span.is_recording():
            span.add_event(name, attributes=attributes)

    def create_span(self, name: str) -> trace.Span:
        """Create a new span"""
        return self.tracer.start_span(name)
