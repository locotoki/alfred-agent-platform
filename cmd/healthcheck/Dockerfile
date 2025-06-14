FROM golang:1.22-alpine as builder

WORKDIR /app

# Copy go.mod and go.sum
COPY go.mod go.sum ./
RUN go mod download

# Copy the source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -o /healthcheck ./cmd/healthcheck

# Create a minimal runtime image
FROM alpine:3.19

WORKDIR /

COPY --from=builder /healthcheck /healthcheck

# Set the entrypoint
ENTRYPOINT ["/healthcheck"]

# Security: Run as non-root user
USER 1001
