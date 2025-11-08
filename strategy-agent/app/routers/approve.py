"""Approve endpoint - HITL approval with Pub/Sub publishing."""

import logging

from fastapi import APIRouter, HTTPException
from promote_autonomy_shared.schemas import JobStatus

from app.models.request import ApproveRequest
from app.models.response import ApproveResponse, ErrorResponse
from app.services.firestore import get_firestore_service
from app.services.pubsub import get_pubsub_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/approve",
    response_model=ApproveResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def approve(request: ApproveRequest):
    """
    Approve a pending job and trigger asset generation.

    This endpoint implements the critical HITL workflow:
    1. Verifies user owns the job
    2. Uses Firestore transaction to atomically transition
       pending_approval → processing
    3. Publishes task to Pub/Sub for Creative Agent
    4. Returns success confirmation

    Error cases:
    - 403: User does not own the job
    - 404: Job not found
    - 409: Job not in pending_approval status (already processed)
    - 500: Transaction or publish failed
    """
    try:
        logger.info(
            f"Processing approval request for job {request.event_id} "
            f"by user {request.uid}"
        )

        firestore_service = get_firestore_service()

        # Atomic approval transaction
        try:
            job = await firestore_service.approve_job(request.event_id, request.uid)
        except ValueError as e:
            if "not found" in str(e):
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {request.event_id} not found",
                )
            elif "expected pending_approval" in str(e):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Job {request.event_id} is not in pending_approval status. "
                        "It may have already been processed."
                    ),
                )
            else:
                raise
        except PermissionError as e:
            raise HTTPException(
                status_code=403,
                detail=str(e),
            )

        # Publish to Pub/Sub (only after successful transaction)
        pubsub_service = get_pubsub_service()
        message_id = await pubsub_service.publish_task(
            request.event_id,
            job.task_list,
        )

        logger.info(
            f"Approved job {request.event_id}, status -> {job.status}, "
            f"published message {message_id}"
        )

        return ApproveResponse(
            event_id=request.event_id,
            status=JobStatus.PROCESSING,
            message="Job approved and sent for processing",
            published=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in approve endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve job: {str(e)}",
        )
