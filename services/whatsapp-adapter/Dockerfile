FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/

# Security: Run as non-root user
USER 1001

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8080"]
