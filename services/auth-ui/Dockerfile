FROM ghcr.io/locotoki/alfred-agent-platform-v2/healthcheck:0.4.0 AS healthcheck

FROM nginx:stable-alpine
COPY --from=healthcheck /usr/local/bin/healthcheck /usr/local/bin/healthcheck
RUN chmod +x /usr/local/bin/healthcheck

# Copy custom nginx config if needed
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static files
COPY ./dist /usr/share/nginx/html

# Create health endpoint
RUN mkdir -p /usr/share/nginx/html/health && \
    echo '{"status":"healthy"}' > /usr/share/nginx/html/health/index.json

# Expose HTTP and metrics ports
EXPOSE 80
EXPOSE 9091

# Start nginx with healthcheck wrapper
CMD ["healthcheck", "--export-prom", ":9091", "--", "nginx", "-g", "daemon off;"]

# Security: Run as non-root user
USER 1001
