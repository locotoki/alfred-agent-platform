FROM ghcr.io/locotoki/alfred-agent-platform-v2/healthcheck:0.4.0 AS healthcheck
FROM node:18.20.5-alpine3.20
COPY --from=healthcheck /usr/local/bin/healthcheck /usr/local/bin/healthcheck


WORKDIR /app

# Copy package.json and create a minimal package
COPY package.json .
RUN echo '{"name":"mock-storage-api","version":"1.0.0","private":true}' > package.json && \
    npm install express cors

# Copy mock storage service
COPY mock-storage.js .

# Expose port
EXPOSE 5000
EXPOSE 9091
#  Metrics port

# Security: Run as non-root user
USER 1001

# Start the mock service
CMD ["healthcheck", "--export-prom", ":9091", "--", "node", "mock-storage.js"]
