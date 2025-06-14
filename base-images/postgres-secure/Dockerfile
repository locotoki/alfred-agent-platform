# Security-hardened PostgreSQL image
# Addresses vulnerabilities in postgres:15-alpine-hardened including gosu CVEs
FROM postgres:16.6-alpine3.20 AS base

# Update Alpine packages to latest patch versions
RUN apk update && apk upgrade && \
    apk add --no-cache \
    curl \
    && rm -rf /var/cache/apk/*

# Remove or update vulnerable gosu binary (replace with su-exec which is more secure)
RUN apk del gosu || true && \
    apk add --no-cache su-exec

# Create custom entrypoint that uses su-exec instead of gosu
COPY base-images/postgres-secure/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Security hardening
RUN chmod 700 /var/lib/postgresql/data || true

# Use updated Alpine libxml2 to address CVE-2025-32414 and CVE-2025-32415
RUN apk add --update-cache --repository https://dl-cdn.alpinelinux.org/alpine/edge/main \
    libxml2 || apk add --no-cache libxml2

# Expose standard PostgreSQL port
EXPOSE 5432

# Security: Run as non-root user
USER 1001

# Use custom entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["postgres"]