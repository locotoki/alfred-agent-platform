FROM ghcr.io/locotoki/alfred-agent-platform-v2/healthcheck:0.4.0 AS healthcheck

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (for better layer caching)
COPY services/db-metrics/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY services/db-metrics/app.py /app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV METRICS_PORT=9091

# Expose ports
EXPOSE 8000
EXPOSE 9091

# Add health check
HEALTHCHECK --interval=30s --timeout=20s --start-period=45s --retries=5 \
  CMD curl -f http://localhost:8000/healthz || exit 1

# Security: Run as non-root user
USER 1001

# Run the application
CMD ["python", "app.py"]
