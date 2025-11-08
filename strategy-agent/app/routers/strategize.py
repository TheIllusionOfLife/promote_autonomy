"""Strategize endpoint - generate marketing strategy."""

import logging

from fastapi import APIRouter, HTTPException
from ulid import ULID

from app.models.request import StrategizeRequest
from app.models.response import ErrorResponse, StrategizeResponse
from app.services.firestore import get_firestore_service
from app.services.gemini import get_gemini_service
from promote_autonomy_shared.schemas import JobStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/strategize",
    response_model=StrategizeResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def strategize(request: StrategizeRequest):
    """
    Generate a marketing strategy from a high-level goal.

    This endpoint:
    1. Uses Gemini AI to generate a structured task list
    2. Creates a job in Firestore with status=pending_approval
    3. Returns the event_id for the user to review and approve

    The job remains in pending_approval until the user calls /approve.
    """
    try:
        # Generate unique event ID
        event_id = str(ULID())
        logger.info(f"Processing strategize request for user {request.uid}")

        # Generate task list via Gemini
        gemini_service = get_gemini_service()
        task_list = await gemini_service.generate_task_list(request.goal)

        # Create job in Firestore
        firestore_service = get_firestore_service()
        job = await firestore_service.create_job(event_id, request.uid, task_list)

        logger.info(
            f"Created job {event_id} for user {request.uid} "
            f"with status {job.status}"
        )

        return StrategizeResponse(
            event_id=event_id,
            status=JobStatus.PENDING_APPROVAL,
            message="Strategy generated successfully. Please review and approve.",
        )

    except Exception as e:
        logger.error(f"Error in strategize endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate strategy: {str(e)}",
        )
