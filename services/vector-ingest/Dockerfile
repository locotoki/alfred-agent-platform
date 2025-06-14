FROM python:3.11-slim
WORKDIR /app

# Security: Update base packages
RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip

# Install lightweight dependencies first
RUN pip install --no-cache-dir fastapi uvicorn[standard] requests cloudevents

# Note: Commenting out heavy ML deps for P0 fix - service will be minimal but functional
# RUN pip install --no-cache-dir langchain sentence-transformers
# Will need proper ML base image for full functionality

COPY worker.py .

# Security: Run as non-root user  
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "worker.py"]
# Security: Run as non-root user
USER 1001
