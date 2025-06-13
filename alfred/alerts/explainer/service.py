"""Alert Explainer Service API.

This module implements a FastAPI service that provides alert explanation
functionality via a REST API interface.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .agent import ExplainerAgent

# Configure logging
logger = structlog.get_logger(__name__)
# Initialize the agent
agent = ExplainerAgent()


class AlertExplanationRequest(BaseModel):
    """Schema for an alert explanation request"""

    alert_name: str = Field(..., description="The name of the alert")
    description: Optional[str] = Field(None, description="Alert description")
    labels: Optional[Dict[str, str]] = Field(None, description="Alert labels")
    annotations: Optional[Dict[str, str]] = Field(None, description="Alert annotations")
    value: Optional[str] = Field(None, description="Current metric value")
    startsAt: Optional[str] = Field(None, description="Alert start time")
    endsAt: Optional[str] = Field(None, description="Alert end time (if resolved)")


class AlertExplanationResponse(BaseModel):
    """Schema for an alert explanation response"""

    alert_name: str
    explanation: str
    success: bool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager"""
    logger.info("Starting Alert Explainer Service")
    yield
    logger.info("Shutting down Alert Explainer Service")


app = FastAPI(
    title="Alert Explainer API",
    description="API for explaining alerts in natural language",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "service": "alert-explainer"}


@app.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """Readiness check endpoint"""
    return {"status": "ready", "service": "alert-explainer"}


@app.post("/api/v1/explain", response_model=AlertExplanationResponse)
async def explain_alert(request: AlertExplanationRequest) -> JSONResponse:
    """Explain an alert in natural language.

    Args:
        request: The alert explanation request

    Returns:
        A JSON response with the explanation
    """
    logger.info(
        "alert_explanation_request",
        alert_name=request.alert_name,
        has_description=bool(request.description),
    )

    # Convert request to dict for the agent
    alert_data = request.dict()

    # Call the agent to explain the alert
    result = await agent.explain_alert(alert_data)

    if not result.get("success", False):
        logger.error(
            "alert_explanation_failed",
            alert_name=request.alert_name,
            error=result.get("error", "Unknown error"),
        )
        raise HTTPException(status_code=500, detail="Failed to generate explanation")

    explanation = result.get("explanation", "")
    logger.info(
        "alert_explanation_success",
        alert_name=request.alert_name,
        explanation_length=len(explanation) if isinstance(explanation, str) else 0,
    )

    return JSONResponse(
        content={
            "alert_name": result.get("alert_name", request.alert_name),
            "explanation": result.get("explanation", ""),
            "success": True,
        }
    )


@app.post("/api/v1/webhook/prometheus")
async def prometheus_webhook(request: Request) -> Dict[str, Any]:
    """Handle Prometheus Alertmanager webhook.

    Args:
        request: The webhook request

    Returns:
        A status response
    """
    try:
        payload = await request.json()
        logger.info(
            "prometheus_webhook_received",
            alerts_count=len(payload.get("alerts", [])),
        )

        # Process alerts asynchronously
        asyncio.create_task(process_prometheus_alerts(payload))

        return {"status": "processing", "alerts_count": len(payload.get("alerts", []))}

    except Exception as e:
        logger.error(
            "prometheus_webhook_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=400, detail="Invalid Prometheus Alertmanager payload")


async def process_prometheus_alerts(payload: Dict[str, Any]) -> None:
    """Process Prometheus alerts asynchronously.

    Args:
        payload: The Prometheus Alertmanager payload
    """
    alerts = payload.get("alerts", [])

    for alert in alerts:
        try:
            # Convert Prometheus alert format to our format
            alert_request = AlertExplanationRequest(
                alert_name=alert.get("labels", {}).get("alertname", "Unknown Alert"),
                description=alert.get("annotations", {}).get("description", ""),
                labels=alert.get("labels", {}),
                annotations=alert.get("annotations", {}),
                value=alert.get("annotations", {}).get("value", ""),
                startsAt=alert.get("startsAt", ""),
                endsAt=alert.get("endsAt", ""),
            )

            # Generate explanation
            result = await agent.explain_alert(alert_request.dict())

            logger.info(
                "alert_processed",
                alert_name=alert_request.alert_name,
                success=result.get("success", False),
            )

        except Exception as e:
            logger.error(
                "alert_processing_error",
                error=str(e),
                error_type=type(e).__name__,
            )
