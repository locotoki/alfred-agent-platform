FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends redis-server curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app
WORKDIR /app

# Security: Run as non-root user
USER 1001

ENTRYPOINT ["python", "simple_bot.py"]
