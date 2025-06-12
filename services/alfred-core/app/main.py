"""Alfred Core Service - Main application entry point."""

import time
import httpx
import json
from typing import Dict, Any

import structlog
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest

# Configure structured logging
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(title="Alfred Core Service", version="0.9.6")

# Prometheus metrics
request_count = Counter(
    "alfred_core_requests_total", "Total requests", ["method", "endpoint", "status"]
)
request_duration = Histogram(
    "alfred_core_request_duration_seconds", "Request duration", ["method", "endpoint"]
)


async def call_ollama(prompt: str) -> str:
    """Call Ollama LLM service"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://llm-service:11434/api/generate",
                json={
                    "model": "llama3:8b",
                    "prompt": f"System: You are Alfred, a helpful AI assistant for the Alfred Agent Platform. Be friendly, helpful, and informative.\n\nHuman: {prompt}\n\nAssistant:",
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 500},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "I apologize, but I couldn't generate a response.")
    except Exception as e:
        logger.error("Error calling Ollama", error=str(e))
        return f"I encountered an error: {str(e)}"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "alfred-core",
        "version": "0.9.6",
        "timestamp": int(time.time()),
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.get("/")
async def root():
    """Root endpoint."""
    request_count.labels(method="GET", endpoint="/", status="200").inc()
    return {
        "service": "alfred-core",
        "status": "operational",
        "endpoints": {"health": "/health", "metrics": "/metrics", "api": "/api/v1"},
    }


@app.get("/api/v1/status")
async def api_status():
    """Return API status."""
    with request_duration.labels(method="GET", endpoint="/api/v1/status").time():
        request_count.labels(method="GET", endpoint="/api/v1/status", status="200").inc()
        logger.info("Status check requested")
        return {
            "api_version": "v1",
            "status": "active",
            "capabilities": [
                "agent-orchestration",
                "task-routing",
                "metric-collection",
                "llm-chat",
            ],
        }


@app.post("/api/v1/tasks")
async def create_task(task: dict):
    """Create a new task (placeholder)."""
    request_count.labels(method="POST", endpoint="/api/v1/tasks", status="201").inc()
    logger.info("Task created", task_id=task.get("id", "unknown"))
    return {"task_id": "task-123", "status": "queued", "message": "Task queued for processing"}


@app.post("/api/v1/chat")
async def chat(request: dict):
    """Chat endpoint for UI integration."""
    request_count.labels(method="POST", endpoint="/api/v1/chat", status="200").inc()
    logger.info("Chat request received", question=request.get("question", ""))

    question = request.get("question", "")
    model = request.get("model", "llama3:8b")

    try:
        response = await call_ollama(question)

        return {
            "response": response,
            "model": model,
            "timestamp": int(time.time()),
            "status": "success",
        }
    except Exception as e:
        logger.error("Error in chat endpoint", error=str(e))
        return {
            "response": "I apologize, but I encountered an error processing your request. Please try again.",
            "model": model,
            "timestamp": int(time.time()),
            "status": "error",
        }


@app.post("/query")
async def query(request: dict):
    """Alternative query endpoint for compatibility."""
    request_count.labels(method="POST", endpoint="/query", status="200").inc()
    logger.info("Query request received", question=request.get("question", ""))

    question = request.get("question", "")

    try:
        answer = await call_ollama(question)

        return {
            "answer": answer,
            "question": question,
            "timestamp": int(time.time()),
            "status": "success",
        }
    except Exception as e:
        logger.error("Error in query endpoint", error=str(e))
        return {
            "answer": "I apologize, but I encountered an error processing your request.",
            "question": question,
            "timestamp": int(time.time()),
            "status": "error",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8011)
