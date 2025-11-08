"""Approve endpoint - HITL approval with Pub/Sub publishing."""

import logging

from fastapi import APIRouter, HTTPException, Header
from firebase_admin import auth
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
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def approve(request: ApproveRequest, authorization: str = Header(None)):
    """
    Approve a pending job and trigger asset generation.

    This endpoint implements the critical HITL workflow:
    1. Verifies Firebase ID token from Authorization header
    2. Verifies user owns the job
    3. Uses Firestore transaction to atomically transition
       pending_approval → processing
    4. Publishes task to Pub/Sub for Creative Agent
    5. Returns success confirmation

    Error cases:
    - 401: Missing or invalid Firebase ID token
    - 403: User does not own the job or UID mismatch
    - 404: Job not found
    - 409: Job not in pending_approval status (already processed)
    - 500: Transaction or publish failed
    """
    try:
        # Verify Firebase ID token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid authorization header",
            )

        id_token = authorization.split("Bearer ")[1]
        try:
            decoded_token = auth.verify_id_token(id_token)
            token_uid = decoded_token["uid"]
        except Exception as e:
            logger.warning(f"Invalid Firebase ID token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid Firebase ID token",
            )

        # Verify UID from token matches UID in request
        if token_uid != request.uid:
            logger.warning(
                f"UID mismatch: token={token_uid}, request={request.uid}"
            )
            raise HTTPException(
                status_code=403,
                detail="UID mismatch between token and request",
            )

        logger.info(
            f"Verified Firebase token for user {token_uid}, "
            f"processing approval for job {request.event_id}"
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
        # If publish fails, revert job to pending_approval
        pubsub_service = get_pubsub_service()
        try:
            message_id = await pubsub_service.publish_task(
                request.event_id,
                job.task_list,
            )
            logger.info(
                f"Approved job {request.event_id}, status -> {job.status}, "
                f"published message {message_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish job {request.event_id} to Pub/Sub: {e}",
                exc_info=True,
            )
            # Rollback: revert job to pending_approval
            rollback_succeeded = False
            try:
                await firestore_service.revert_to_pending(request.event_id)
                logger.info(f"Reverted job {request.event_id} to pending_approval")
                rollback_succeeded = True
            except Exception as rollback_error:
                logger.error(
                    f"CRITICAL: Failed to rollback job {request.event_id}: "
                    f"{rollback_error}",
                    exc_info=True,
                )

            if rollback_succeeded:
                detail_msg = (
                    "Failed to publish job to processing queue. "
                    "Job has been reverted to pending_approval. Please try again."
                )
            else:
                detail_msg = (
                    "CRITICAL: Failed to publish job AND failed to rollback. "
                    f"Job {request.event_id} is stuck in PROCESSING state. "
                    "Contact system administrator for manual intervention."
                )

            raise HTTPException(
                status_code=500,
                detail=detail_msg,
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
