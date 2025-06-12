import time
from functools import wraps
from typing import Callable

import structlog
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)
class MetricsCollector:
    def __init__(self, service_name: str):
        self.service_name = service_name

        # Task metrics
        self.task_counter = Counter(
            "tasks_total", "Total number of tasks", ["service", "intent", "status"]
        )

        self.task_duration = Histogram(
            "task_processing_duration_seconds",
            "Task processing duration",
            ["service", "intent"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        self.active_tasks = Gauge("tasks_active", "Number of active tasks", ["service"])

        # API metrics
        self.api_requests = Counter(
            "api_requests_total",
            "Total API requests",
            ["service", "endpoint", "method", "status"],
        )

        self.api_latency = Histogram(
            "api_request_duration_seconds",
            "API request duration",
            ["service", "endpoint", "method"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        # Error metrics
        self.error_counter = Counter(
            "errors_total", "Total number of errors", ["service", "type", "operation"]
        )

        # PubSub metrics
        self.pubsub_messages = Counter(
            "pubsub_messages_total",
            "Total Pub/Sub messages",
            ["service", "topic", "operation"],
        )

        self.pubsub_latency = Histogram(
            "pubsub_operation_duration_seconds",
            "Pub/Sub operation duration",
            ["service", "operation"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
        )

    def track_task(self, intent: str):
        """Decorator to track task metrics"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                self.active_tasks.labels(service=self.service_name).inc()
                start_time = time.time()

                try:
                    result = await func(*args, **kwargs)
                    self.task_counter.labels(
                        service=self.service_name, intent=intent, status="success"
                    ).inc()
                    return result

                except Exception as e:
                    self.task_counter.labels(
                        service=self.service_name, intent=intent, status="error"
                    ).inc()
                    self.error_counter.labels(
                        service=self.service_name,
                        type=type(e).__name__,
                        operation="task_processing",
                    ).inc()
                    raise

                finally:
                    duration = time.time() - start_time
                    self.task_duration.labels(service=self.service_name, intent=intent).observe(
                        duration
                    )
                    self.active_tasks.labels(service=self.service_name).dec()

            return wrapper

        return decorator

    def track_api(self, endpoint: str, method: str):
        """Decorator to track API metrics"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"

                try:
                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    status = "error"
                    self.error_counter.labels(
                        service=self.service_name,
                        type=type(e).__name__,
                        operation="api_request",
                    ).inc()
                    raise

                finally:
                    duration = time.time() - start_time
                    self.api_requests.labels(
                        service=self.service_name,
                        endpoint=endpoint,
                        method=method,
                        status=status,
                    ).inc()
                    self.api_latency.labels(
                        service=self.service_name, endpoint=endpoint, method=method
                    ).observe(duration)

            return wrapper

        return decorator

    def track_pubsub(self, topic: str, operation: str):
        """Track Pub/Sub metrics"""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()

                try:
                    result = await func(*args, **kwargs)
                    self.pubsub_messages.labels(
                        service=self.service_name, topic=topic, operation=operation
                    ).inc()
                    return result

                except Exception as e:
                    self.error_counter.labels(
                        service=self.service_name,
                        type=type(e).__name__,
                        operation=f"pubsub_{operation}",
                    ).inc()
                    raise

                finally:
                    duration = time.time() - start_time
                    self.pubsub_latency.labels(
                        service=self.service_name, operation=operation
                    ).observe(duration)

            return wrapper

        return decorator
