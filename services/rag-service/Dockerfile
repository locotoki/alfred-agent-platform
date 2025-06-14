FROM ghcr.io/locotoki/alfred-agent-platform-v2/healthcheck:0.4.0 AS healthcheck

FROM python:3.11-slim
COPY --from=healthcheck /usr/local/bin/healthcheck /usr/local/bin/healthcheck
RUN chmod +x /usr/local/bin/healthcheck

WORKDIR /app

# Install dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Healthcheck is handled by the healthcheck binary

# Expose application port
EXPOSE 8501
# Expose metrics port for Prometheus
EXPOSE 9091

# Start the application with healthcheck metrics exporter
# DO NOT REMOVE --export-prom FLAG - Required for Prometheus metrics collection
CMD ["bash", "-c", "healthcheck serve --export-prom :9091 & exec uvicorn app.main:app --host 0.0.0.0 --port 8501"]

# Security: Run as non-root user
USER 1001
