FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn
COPY router_stub.py .
HEALTHCHECK --interval=10s --start-period=15s CMD curl -f http://localhost:8080/health || exit 1

# Security: Run as non-root user
USER 1001

CMD ["uvicorn", "router_stub:app", "--host", "0.0.0.0", "--port", "8080"]
