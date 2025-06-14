ARG ASSETS=assets
FROM python:3.11.10-slim

# Make ASSETS available as environment variable
ARG ASSETS
ENV ASSETS=${ASSETS}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/alfred-core/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/alfred-core/app /app/app
COPY services/alfred-core/${ASSETS}/health.json /app/health.json
COPY healthcheck/healthcheck.sh /usr/local/bin/healthcheck.sh

# Make healthcheck script executable
RUN chmod +x /usr/local/bin/healthcheck.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose application port and metrics port
EXPOSE 8011
EXPOSE 9091

# Security: Run as non-root user
USER 1001

# Run the application with metrics export
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
