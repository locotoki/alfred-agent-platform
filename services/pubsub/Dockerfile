FROM ghcr.io/locotoki/alfred-agent-platform-v2/healthcheck:0.4.0 AS healthcheck

FROM gcr.io/google.com/cloudsdktool/cloud-sdk:latest


# Install Python and pip for the health check wrapper
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv curl && rm -rf /var/lib/apt/lists/*

# Create and use virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install dependencies
COPY services/pubsub/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the health check wrapper
COPY services/pubsub/health_wrapper.py /app/

# Expose ports for PubSub emulator and metrics
EXPOSE 8085
EXPOSE 9091

# Set entrypoint script
COPY services/pubsub/entrypoint.sh /
RUN chmod +x /entrypoint.sh

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=20s --retries=5 --start-period=45s \
  CMD curl -f http://localhost:9091/health || exit 1

# Run both PubSub emulator and the health check wrapper
COPY services/pubsub/entrypoint.init.sh /entrypoint.init.sh
CMD ["sh","/entrypoint.init.sh"]

# Security: Run as non-root user
USER 1001
