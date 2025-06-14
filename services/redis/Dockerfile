# First stage: Get the healthcheck binary
FROM gcr.io/distroless/static-debian12:nonroot AS healthcheck
WORKDIR /app
COPY --from=ghcr.io/alfred-health/healthcheck:latest /usr/local/bin/healthcheck /usr/local/bin/healthcheck

# Main application stage
FROM redis:7.4-alpine3.20 AS app

# Install Python and pip for Redis services
RUN apk add --no-cache python3 py3-pip curl

# Create and use virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install healthcheck binary from first stage
COPY --from=healthcheck /usr/local/bin/healthcheck /usr/local/bin/healthcheck

# Set up health check environment variables
ENV HEALTH_CHECK_PORT=9091
ENV HEALTH_CHECK_PATH=/health
ENV HEALTH_CHECK_INTERVAL=30s
ENV METRICS_EXPORTER_PORT=9091

# Copy application code
COPY health_wrapper.py /app/

# Set healthcheck command with standard parameters
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/usr/local/bin/healthcheck", \
         "--export-prom", ":${METRICS_EXPORTER_PORT}", \
         "--interval", "${HEALTH_CHECK_INTERVAL}", \
         "--port", "${HEALTH_CHECK_PORT}", \
         "--path", "${HEALTH_CHECK_PATH}"]

# Copy and prepare the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose ports for Redis and metrics
EXPOSE 6379
EXPOSE 9091

# Use the entrypoint script to run the application
ENTRYPOINT ["/app/entrypoint.sh"]

# Security: Run as non-root user
USER 1001
