# Dockerfile for Slack diagnostics bot
FROM python:3.11-slim

# Environment configuration
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY alfred /app/alfred

# Security: Run as non-root user
USER 1001

# Run the diagnostics bot
CMD ["python", "-m", "alfred.slack.diagnostics"]
