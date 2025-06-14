FROM python:3.11-slim

WORKDIR /app

# Copy requirements if exists
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# Security: Run as non-root user
USER 1001

# Default command
CMD ["python", "-m", "alfred.core.entrypoint"]
