# Multi-stage Dockerfile for dev container hardening
# ADR-010: Prevent host system package contamination

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install yq
RUN wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 && \
    chmod +x /usr/local/bin/yq

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Set working directory
WORKDIR /workspace

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies in a virtual environment
RUN python -m venv .venv && \
    . .venv/bin/activate && \
    poetry install --no-root --no-interaction --no-ansi

# Copy requirements.txt if it exists and install with pip (avoid layer bloat)
COPY requirements.txt* ./
RUN . .venv/bin/activate && \
    if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Stage 2: Runtime
FROM python:3.11-slim as runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy only app and venv from builder
COPY --from=builder /workspace/.venv /workspace/.venv
COPY . /app

# Set PYTHONPATH explicitly (preserving runtime additions)
ENV PYTHONPATH=/workspace/.venv/lib/python3.11/site-packages:${PYTHONPATH}
ENV PATH="/workspace/.venv/bin:$PATH"

# Verify no system packages contamination
RUN test -z "$(find /usr/lib/python*/dist-packages -type f)" || \
    (echo "ERROR: System packages found in dist-packages!" && exit 1)

# Security: Run as non-root user
USER 1001

# Default command
CMD ["/bin/bash"]
