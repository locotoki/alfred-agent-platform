# alfred/metrics/Dockerfile  – pubsub-metrics
FROM python:3.11-slim

# 1. system deps for prometheus_client + curl (health probes)
RUN apt-get update -qq && apt-get install -y --no-install-recommends curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. copy deps first for layer-caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. copy your tiny FastAPI app
COPY app.py .

# 4. Health-check: hit the /health route exposed by app.py
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -fs http://localhost:9103/health || exit 1

EXPOSE 9103

# Security: Run as non-root user
USER 1001

# 5. Run with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9103"]
