FROM ghcr.io/locotoki/alfred-agent-platform-v2/healthcheck:0.4.0 AS healthcheck

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir streamlit requests fastapi uvicorn

# Copy application code
COPY streamlit_chat.py .
COPY health_server.py .

# Expose Streamlit port and health check port
EXPOSE 8501
EXPOSE 8080
EXPOSE 9091

# Set environment variables
ENV ALFRED_API_URL=http://agent-core:8011
ENV ALFRED_MODEL_ROUTER_URL=http://model-router:8080
ENV ENABLE_DIRECT_INFERENCE=true

# Simple health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8501 || exit 1

# Security: Run as non-root user
USER 1001

# Run both streamlit and health server
CMD ["sh", "-c", "streamlit run streamlit_chat.py --server.address=0.0.0.0 & uvicorn health_server:app --host 0.0.0.0 --port 8080"]
