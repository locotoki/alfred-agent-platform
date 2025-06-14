FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 8080

FROM base AS build
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
RUN npm install -g serve@14.2.1
COPY --from=build /app/dist ./dist
EXPOSE 8080

# Security: Run as non-root user
USER 1001

CMD ["serve", "-s", "dist", "-l", "8080"]
