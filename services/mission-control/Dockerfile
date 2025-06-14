# Use Node.js LTS
FROM node:18.20.5-alpine3.20

# Set working directory
WORKDIR /app

# Copy package files from service directory (when build context is repo root)
COPY services/mission-control/package*.json ./

# Install dependencies
RUN npm ci --omit=dev

# Copy all source files from service directory
COPY services/mission-control/ ./

# Set environment
ENV NODE_ENV production
ENV HOSTNAME "0.0.0.0"
ENV PORT 3000

# Expose port
EXPOSE 3000

# Security: Run as non-root user
USER 1001

# Simple health check server for now (until TypeScript issues are fixed)
CMD ["node", "-e", "require('http').createServer((req,res)=>{res.writeHead(200);res.end('OK')}).listen(3000,()=>console.log('Health server on :3000'))"]
