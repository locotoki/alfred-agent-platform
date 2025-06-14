FROM postgres:15.5-alpine

# This is a placeholder image to unblock GA workflows
# It extends the standard PostgreSQL image with custom configurations

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD pg_isready -U postgres || exit 1

# Set default environment variables
ENV POSTGRES_DB=alfred_storage
ENV POSTGRES_USER=postgres

# Expose PostgreSQL port
EXPOSE 5432

# Use the default entrypoint from the base image
# In production, this would include custom initialization scripts

# Security: Run as non-root user
USER 1001
