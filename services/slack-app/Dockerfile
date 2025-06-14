FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Default port for API
EXPOSE 8080

# Default port for metrics
EXPOSE 8081

# Security: Run as non-root user
USER 1001

# Start the application
CMD ["uvicorn", "slack_app.server:app", "--host", "0.0.0.0", "--port", "8080"]
