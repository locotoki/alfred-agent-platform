FROM ghcr.io/locotoki/alfred-agent-platform-v2/healthcheck:0.4.0 AS healthcheck

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy healthcheck binary
COPY --from=healthcheck /healthcheck /usr/local/bin/healthcheck

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose application port
EXPOSE 8000
# Expose metrics port for Prometheus
EXPOSE 9091

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Start the application with healthcheck metrics exporter
# DO NOT REMOVE --export-prom FLAG - Required for Prometheus metrics collection
CMD ["bash", "-c", "healthcheck serve --export-prom :9091 & exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# Security: Run as non-root user
USER 1001
