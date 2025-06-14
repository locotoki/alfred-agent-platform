FROM node:18-alpine

WORKDIR /app

# Copy package dependencies
COPY package.json ./
COPY package-lock.json* ./

# Install dependencies
RUN npm install

# Copy server files
COPY server.js ./
COPY integrate-with-social-intel.js ./
COPY .env.docker ./.env
COPY tests ./tests
COPY public ./public

# Expose port
EXPOSE 3007

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3007

# Start the application
CMD ["node", "server.js"]

# Security: Run as non-root user
USER 1001
