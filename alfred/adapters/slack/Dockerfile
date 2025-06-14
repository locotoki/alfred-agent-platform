FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY alfred/adapters/slack/requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY alfred/adapters/slack alfred/adapters/slack/
COPY alfred/adapters/__init__.py alfred/adapters/
COPY alfred/__init__.py alfred/

# Set Python path
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Security: Run as non-root user
USER 1001

# Run the application
EXPOSE 8000
CMD ["uvicorn", "alfred.adapters.slack.webhook:app", "--host", "0.0.0.0", "--port", "8000"]
