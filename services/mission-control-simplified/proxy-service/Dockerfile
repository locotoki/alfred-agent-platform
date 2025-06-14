FROM node:18-alpine

# Create app directory
WORKDIR /app

# Install app dependencies
COPY package*.json ./
RUN npm ci --only=production

# Bundle app source
COPY . .

# Expose port for the proxy service
EXPOSE 3020

# Start the service
CMD ["node", "src/index.js"]

# Security: Run as non-root user
USER 1001
