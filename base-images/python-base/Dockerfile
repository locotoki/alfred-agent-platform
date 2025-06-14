# Shared Python base image for Alfred services
# This image provides common Python dependencies and optimizations
FROM python:3.11-slim

# Set environment variables
ENV PIP_ROOT_USER_ACTION=ignore
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install common system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages that most services use
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    structlog \
    prometheus-client \
    httpx \
    tenacity

# Create app directory
WORKDIR /app

# Create non-root user
RUN groupadd -r alfred && useradd -r -g alfred alfred

# Common healthcheck script
COPY healthcheck/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Security: Run as non-root user
USER 1001