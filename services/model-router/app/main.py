"""Model router service main entry point."""

import os

import uvicorn
from fastapi import FastAPI
from prometheus_client import make_asgi_app

app = FastAPI(title="Model Router")
# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "model-router"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Model Router Service", "version": "0.1.0"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
