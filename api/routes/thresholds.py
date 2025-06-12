"""API routes for dynamic threshold management"""

from typing import Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from alfred.ml import ThresholdService

router = APIRouter(prefix="/thresholds", tags=["thresholds"])
class ThresholdUpdate(BaseModel):
    """Request model for threshold updates"""

    noise_threshold: float = Field(None, ge=0.0, le=1.0, description="Noise detection threshold")
    confidence_min: float = Field(None, ge=0.0, le=1.0, description="Minimum confidence threshold")
    batch_size: int = Field(None, ge=1, le=1000, description="Processing batch size")
    learning_rate: float = Field(None, ge=0.0001, le=1.0, description="Model learning rate")

class ThresholdResponse(BaseModel):
    """Response model for threshold queries"""

    noise_threshold: float
    confidence_min: float
    batch_size: int
    learning_rate: float

# Initialize the threshold service
threshold_service = ThresholdService()

@router.get("", response_model=ThresholdResponse)
async def get_thresholds() -> ThresholdResponse:
    """Get current threshold configuration.

    Returns:
        Current threshold values.

    """
    thresholds = threshold_service.get_thresholds()
    return ThresholdResponse(**thresholds)

@router.patch("", response_model=ThresholdResponse)
async def update_thresholds(updates: ThresholdUpdate) -> ThresholdResponse:
    """Update threshold configuration.

    Args:
        updates: Partial threshold updates

    Returns:
        Updated threshold values

    Raises:
        HTTPException: If update fails.

    """
    try:
        # Filter out None values
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}

        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid updates provided",
            )

        updated = threshold_service.update_thresholds(update_dict)
        return ThresholdResponse(**updated)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update thresholds: {str(e)}",
        )

@router.post("/optimize", response_model=ThresholdResponse)
async def optimize_thresholds(metrics: Dict[str, float]) -> ThresholdResponse:
    """Automatically optimize thresholds based on performance metrics.

    Args:
        metrics: Performance metrics (e.g., false_positive_rate, accuracy)

    Returns:
        Optimized threshold values.

    """
    try:
        optimized = threshold_service.optimize_thresholds(metrics)
        return ThresholdResponse(**optimized)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize thresholds: {str(e)}",
        )
