FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry export --without-hashes -f requirements.txt  < /dev/null |  pip install --no-cache-dir -r /dev/stdin && \\
    pip install --no-cache-dir uvicorn
COPY . .
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
  CMD curl -fs http://localhost:8082/health || exit 1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8082"]

# Security: Run as non-root user
USER 1001
