FROM alpine:latest

# Install required dependencies
RUN apk add --no-cache curl netcat-openbsd

# Copy the healthcheck script
COPY healthcheck.sh /usr/local/bin/healthcheck

# Make it executable
RUN chmod +x /usr/local/bin/healthcheck

# Security: Run as non-root user
USER 1001

# Set the script as the entrypoint
ENTRYPOINT ["/usr/local/bin/healthcheck"]
