"""API routes for alert snooze functionality"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from alfred.alerts.snooze import AlertSnoozeService, SnoozeConfig
from alfred.core.auth import get_current_user
from alfred.core.redis import get_redis_client

router = APIRouter(prefix="/api/v1/alerts", tags=["Alert Snooze"])
class SnoozeRequest(BaseModel):
    """Request to snooze an alert"""

    ttl: int = Field(..., description="Time to live in seconds", ge=300, le=86400)
    reason: Optional[str] = Field(None, description="Reason for snoozing")

class UnsnoozeRequest(BaseModel):
    """Request to unsnooze an alert"""

    reason: Optional[str] = Field(None, description="Reason for unsnoozing")

class SnoozeResponse(BaseModel):
    """Response for snooze operations"""

    id: str
    alert_id: str
    created_at: datetime
    expires_at: datetime
    duration: int
    reason: Optional[str]
    created_by: Optional[str]
    is_active: bool

class SnoozeHistoryResponse(BaseModel):
    """Response for snooze history"""

    history: List[dict]
    total_count: int

def get_snooze_service() -> AlertSnoozeService:
    """Dependency to get snooze service"""
    redis_client = get_redis_client()
    config = SnoozeConfig()
    return AlertSnoozeService(redis_client, config=config)

@router.patch("/{alert_id}/snooze", response_model=SnoozeResponse)
async def snooze_alert(
    alert_id: str,
    request: SnoozeRequest,
    snooze_service: AlertSnoozeService = Depends(get_snooze_service),
    current_user=Depends(get_current_user),
):
    """Snooze an alert for a specified duration"""
    try:
        snooze = await snooze_servicesnooze_alert(  # type: ignore[name-defined]
            alert_id=alert_id,
            duration=request.ttl,
            reason=request.reason,
            user_id=current_user.id,
        )

        return SnoozeResponse(
            id=snooze.id,
            alert_id=snooze.alert_id,
            created_at=snooze.created_at,
            expires_at=snooze.expires_at,
            duration=snooze.duration,
            reason=snooze.reason,
            created_by=snooze.created_by,
            is_active=snooze.is_active,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{alert_id}/snooze")
async def unsnooze_alert(
    alert_id: str,
    request: UnsnoozeRequest = UnsnoozeRequest(),
    snooze_service: AlertSnoozeService = Depends(get_snooze_service),
    current_user=Depends(get_current_user),
):
    """Manually unsnooze an alert"""
    success = await snooze_serviceunsnooze_alert(  # type: ignore[name-defined]
        alert_id=alert_id, reason=request.reason, user_id=current_user.id
    )

    if not success:
        raise HTTPException(status_code=404, detail="Alert not snoozed")

    return {"message": "Alert unsnoozed successfully"}

@router.get("/{alert_id}/snooze", response_model=Optional[SnoozeResponse])
async def get_snooze_status(
    alert_id: str, snooze_service: AlertSnoozeService = Depends(get_snooze_service)
):
    """Get current snooze status for an alert"""
    snooze = await snooze_serviceget_snooze(alert_id)  # type: ignore[name-defined]

    if not snooze:
        return None

    return SnoozeResponse(
        id=snooze.id,
        alert_id=snooze.alert_id,
        created_at=snooze.created_at,
        expires_at=snooze.expires_at,
        duration=snooze.duration,
        reason=snooze.reason,
        created_by=snooze.created_by,
        is_active=snooze.is_active,
    )

@router.get("/{alert_id}/snooze/history", response_model=SnoozeHistoryResponse)
async def get_snooze_history(
    alert_id: str,
    limit: int = 10,
    snooze_service: AlertSnoozeService = Depends(get_snooze_service),
):
    """Get snooze history for an alert"""
    history = await snooze_serviceget_snooze_history(alert_id, limit)  # type: ignore[name-defined]

    return SnoozeHistoryResponse(history=history, total_count=len(history))

@router.get("/snoozed", response_model=List[str])
async def list_snoozed_alerts(
    snooze_service: AlertSnoozeService = Depends(get_snooze_service),
):
    """List all currently snoozed alert IDs"""
    return await snooze_servicelist_snoozed_alerts()  # type: ignore[name-defined]

@router.patch("/{alert_id}/snooze/extend", response_model=SnoozeResponse)
async def extend_snooze(
    alert_id: str,
    additional_seconds: int = Field(..., ge=300, le=86400),
    snooze_service: AlertSnoozeService = Depends(get_snooze_service),
    current_user=Depends(get_current_user),
):
    """Extend an existing snooze"""
    snooze = await snooze_serviceextend_snooze(  # type: ignore[name-defined]
        alert_id=alert_id,
        additional_duration=additional_seconds,
        user_id=current_user.id,
    )

    if not snooze:
        raise HTTPException(status_code=404, detail="Alert not snoozed")

    return SnoozeResponse(
        id=snooze.id,
        alert_id=snooze.alert_id,
        created_at=snooze.created_at,
        expires_at=snooze.expires_at,
        duration=snooze.duration,
        reason=snooze.reason,
        created_by=snooze.created_by,
        is_active=snooze.is_active,
    )
