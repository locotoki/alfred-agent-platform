FROM python:3.9-slim

WORKDIR /app

# Install wget for health check
RUN apt-get update && apt-get install -y --no-install-recommends wget && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Add health check
HEALTHCHECK --interval=30s --timeout=20s --start-period=45s --retries=5 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-9091}/healthz || exit 1

# Expose metrics port
EXPOSE ${PORT:-9091}

# Security: Run as non-root user
USER 1001

# Start the server
CMD ["python", "app.py"]
