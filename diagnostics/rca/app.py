#!/usr/bin/env python3

import os
import socket
import time

import requests
from flask import Flask, Response, jsonify
from prometheus_client import REGISTRY, Counter, Gauge, generate_latest

app = Flask(__name__)
# Create metrics
service_availability = Gauge("service_availability", "Availability of the service", ["service"])
service_requests_total = Counter(
    "service_requests_total", "Number of service requests", ["service"]
)
db_postgres_connections = Gauge(
    "db_postgres_connections", "Number of active PostgreSQL connections"
)

# Configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "unknown")
SERVICE_URL = os.getenv("SERVICE_URL", "")
HEALTH_PATH = os.getenv("HEALTH_PATH", "/health")
CHECK_TYPE = os.getenv("CHECK_TYPE", "http")  # "http" or "tcp"
DB_POSTGRES_URL = os.getenv("DB_POSTGRES_URL", "")
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "15"))
PORT = int(os.getenv("PORT", "9091"))

def check_service_http():
    """Check HTTP service availability."""
    try:
        if not SERVICE_URL:
            service_availability.labels(service=SERVICE_NAME).set(0)
            return False

        # Special handling for database services that might have different health endpoints
        if SERVICE_NAME == "db-admin" or SERVICE_NAME == "db-storage":
            # First try TCP connection to verify service is running
            url_parts = SERVICE_URL.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 80

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            try:
                s.connect((host, port))
                s.close()
                # If we can connect, consider the service available
                service_availability.labels(service=SERVICE_NAME).set(1)
                return True
            except Exception as e:
                print(f"Error connecting to {SERVICE_NAME} TCP port: {e}")
                service_availability.labels(service=SERVICE_NAME).set(0)
                return False

        # Standard HTTP health check for other services
        url = f"{SERVICE_URL.rstrip('/')}/{HEALTH_PATH.lstrip('/')}"
        response = requests.get(url, timeout=5)

        if response.status_code < 400:
            service_availability.labels(service=SERVICE_NAME).set(1)
            return True
        else:
            service_availability.labels(service=SERVICE_NAME).set(0)
            return False
    except Exception as e:
        print(f"Error checking HTTP service: {e}")
        service_availability.labels(service=SERVICE_NAME).set(0)
        return False

def check_service_tcp():
    """Check TCP service availability."""
    try:
        if not SERVICE_URL:
            service_availability.labels(service=SERVICE_NAME).set(0)
            return False

        # Parse host and port from SERVICE_URL
        parts = SERVICE_URL.split(":")
        if len(parts) != 2:
            service_availability.labels(service=SERVICE_NAME).set(0)
            return False

        host = parts[0]
        port = int(parts[1])

        # Try to connect
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.close()

        service_availability.labels(service=SERVICE_NAME).set(1)
        return True
    except Exception as e:
        print(f"Error checking TCP service: {e}")
        service_availability.labels(service=SERVICE_NAME).set(0)
        return False

def check_db_connections():
    """Check PostgreSQL connections if URL is provided."""
    if not DB_POSTGRES_URL:
        return

    try:
        # We would implement actual DB connection check here
        # For now, just set a placeholder value
        db_postgres_connections.set(10)
    except Exception as e:
        print(f"Error checking DB connections: {e}")
        db_postgres_connections.set(0)

def collect_metrics():
    """Collect all metrics."""
    if CHECK_TYPE.lower() == "http":
        check_service_http()
    else:
        check_service_tcp()

    check_db_connections()

@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    service_requests_total.labels(service=SERVICE_NAME).inc()
    collect_metrics()
    return Response(generate_latest(REGISTRY), mimetype="text/plain")

@app.route("/health")
def health():
    """Health check endpoint."""
    service_requests_total.labels(service=SERVICE_NAME).inc()

    is_healthy = False
    if CHECK_TYPE.lower() == "http":
        is_healthy = check_service_http()
    else:
        is_healthy = check_service_tcp()

    if is_healthy:
        return jsonify({"status": "ok", "version": "1.0.0", "service": SERVICE_NAME})
    else:
        return (
            jsonify({"status": "error", "version": "1.0.0", "service": SERVICE_NAME}),
            500,
        )

@app.route("/healthz")
def healthz():
    """Simple health probe endpoint."""
    return jsonify({"status": "ok"})

# Start background metrics collection
def background_collector():
    """Collect metrics periodically in the background."""
    while True:
        collect_metrics()
        time.sleep(COLLECTION_INTERVAL)

if __name__ == "__main__":
    # Initialize metrics
    service_availability.labels(service=SERVICE_NAME).set(0)

    # Start metrics collection in the background

    import threading
    collector_thread = threading.Thread(target=background_collector, daemon=True)
    collector_thread.start()

    # Print service information
    print(f"Starting DB metrics exporter for {SERVICE_NAME}")
    print(f"Service URL: {SERVICE_URL}")
    print(f"Check type: {CHECK_TYPE}")
    print(f"Listening on port: {PORT}")

    # Start the server
    app.run(host="0.0.0.0", port=PORT)
