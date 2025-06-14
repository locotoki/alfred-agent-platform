FROM python:3.11.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/agent_bizops/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY workflows/ ./workflows/
COPY services/agent_bizops/app/ ./app/

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Security: Run as non-root user
USER 1001

# Run the application
CMD ["python", "-m", "app.main"]
