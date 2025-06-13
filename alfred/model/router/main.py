"""Model Router API for Alfred Agent Platform v2"""

import os
import threading
from datetime import datetime

import httpx
import prometheus_client
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(title="Model Router API")
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MODEL_REGISTRY_URL = os.getenv("MODEL_REGISTRY_URL", "http://model-registry:8079")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "t")


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    # Check model registry connectivity
    registry_status = "ok"
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{MODEL_REGISTRY_URL}/health", timeout=2.0)
    except Exception:
        registry_status = "error"

    # Overall status is ok only if all dependencies are ok
    overall_status = "ok" if registry_status == "ok" else "error"

    return {
        "status": overall_status,
        "version": "1.0.0",
        "services": {"model_registry": registry_status},
    }


@app.get("/healthz")
async def simple_health():
    """Simple health check for container probes"""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint on the main service port"""
    from fastapi.responses import Response

    return Response(content=prometheus_client.generate_latest(), media_type="text/plain")


# Create a separate app to serve metrics on port 9091

metrics_app = FastAPI(title="Model Router Metrics")


@metrics_app.get("/metrics")
async def metrics_export():
    """Prometheus metrics endpoint for port 9091"""
    from fastapi.responses import Response

    return Response(content=prometheus_client.generate_latest(), media_type="text/plain")


# Start metrics server in separate thread when the main app starts
@app.on_event("startup")
async def start_metrics_server():
    """Start metrics server on port 9091"""
    # Start metrics server in a separate thread
    thread = threading.Thread(
        target=uvicorn.run,
        args=(metrics_app,),
        kwargs={"host": "0.0.0.0", "port": 9091, "log_level": "error"},
        daemon=True,
    )
    thread.start()


@app.get("/models")
async def get_models():
    """Get all available models from the registry"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MODEL_REGISTRY_URL}/models")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as exc:
        if DEBUG:
            raise HTTPException(
                status_code=503,
                detail=f"Error connecting to model registry: {str(exc)}",
            )
        else:
            # Return mock data in debug mode if model registry is not available
            return [
                {
                    "id": 1,
                    "name": "gpt-4",
                    "display_name": "GPT-4 Turbo (mock)",
                    "provider": "openai",
                    "model_type": "chat",
                    "description": "Mock GPT-4 model for development",
                },
                {
                    "id": 2,
                    "name": "claude-3-sonnet",
                    "display_name": "Claude 3 Sonnet (mock)",
                    "provider": "anthropic",
                    "model_type": "chat",
                    "description": "Mock Claude 3 model for development",
                },
            ]


@app.post("/completions")
async def get_completion(request: Request):
    """Route completion requests to the appropriate model provider"""
    data = await request.json()
    # In production, this would validate the request and route to the correct model
    return {
        "id": "mock-completion-" + datetime.utcnow().isoformat(),
        "object": "text_completion",
        "created": int(datetime.utcnow().timestamp()),
        "model": data.get("model", "default-mock-model"),
        "choices": [
            {
                "text": "This is a mock completion response for development purposes.",
                "index": 0,
                "finish_reason": "stop",
            }
        ],
    }


@app.post("/chat/completions")
async def get_chat_completion(request: Request):
    """Route chat completion requests to the appropriate model provider"""
    data = await request.json()
    # In production, this would validate the request and route to the correct model
    return {
        "id": "mock-chat-" + datetime.utcnow().isoformat(),
        "object": "chat.completion",
        "created": int(datetime.utcnow().timestamp()),
        "model": data.get("model", "default-mock-model"),
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a mock chat completion response for development purposes.",
                },
                "index": 0,
                "finish_reason": "stop",
            }
        ],
    }


def create_router_app() -> FastAPI:
    """Create and configure the model router app.

    Returns:
        Configured FastAPI application.
    """
    return app
