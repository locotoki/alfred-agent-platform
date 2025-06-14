FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for Prometheus multiprocess metrics
RUN mkdir -p /tmp/prometheus && chmod 777 /tmp/prometheus

# Copy application code
COPY . .

# Create a simple healthcheck script
RUN echo '#!/bin/sh\ncurl -f http://localhost:$PORT/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Expose port
EXPOSE $PORT

# Set health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 CMD ["/app/healthcheck.sh"]

# Security: Run as non-root user
USER 1001

# Command to run the application
CMD ["/app/start.sh"]
