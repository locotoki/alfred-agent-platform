FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY services/slack_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port for HTTP and health checks
EXPOSE 3000

# Set the environment variable for the app
ENV PYTHONUNBUFFERED=1

# Define healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/healthz || exit 1

# Security: Run as non-root user
USER 1001

# Run the app
CMD ["python", "run.py"]
