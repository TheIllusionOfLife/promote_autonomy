"""Strategize endpoint - generate marketing strategy."""

import logging

from fastapi import APIRouter, Header, HTTPException
from firebase_admin import auth
from ulid import ULID

from app.models.request import StrategizeRequest
from app.models.response import ErrorResponse, StrategizeResponse
from app.services.firestore import get_firestore_service
from app.services.gemini import get_gemini_service
from promote_autonomy_shared.schemas import JobStatus, Platform, PLATFORM_SPECS

logger = logging.getLogger(__name__)
router = APIRouter()


def _detect_aspect_ratio_conflicts(platforms: list[Platform]) -> list[str]:
    """Detect aspect ratio conflicts between selected platforms.

    Returns list of warning messages about incompatible aspect ratios.
    """
    if len(platforms) <= 1:
        return []  # No conflicts possible with single platform

    warnings = []
    aspect_ratios = {p: PLATFORM_SPECS[p].image_aspect_ratio for p in platforms}

    # Group platforms by aspect ratio category
    portrait = []  # 9:16
    square = []    # 1:1
    landscape = []  # 16:9, 1.91:1

    for platform, ratio in aspect_ratios.items():
        if ratio == "9:16":
            portrait.append(platform)
        elif ratio == "1:1":
            square.append(platform)
        else:  # 16:9, 1.91:1, etc
            landscape.append(platform)

    # Check for conflicts between categories
    used_categories = sum(1 for category in [portrait, square, landscape] if category)

    if used_categories > 1:
        # Get the first platform (the one that will be used)
        first_platform = platforms[0]
        first_ratio = aspect_ratios[first_platform]

        # List conflicting platforms
        conflicting = [
            f"{p.value} ({aspect_ratios[p]})"
            for p in platforms[1:]
            if aspect_ratios[p] != first_ratio
        ]

        if conflicting:
            conflicting_str = ", ".join(conflicting)
            warnings.append(
                f"Selected platforms have conflicting aspect ratios. "
                f"Assets will use {first_platform.value} format ({first_ratio}). "
                f"Conflicting platforms: {conflicting_str}"
            )

    return warnings


@router.post(
    "/strategize",
    response_model=StrategizeResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def strategize(
    request: StrategizeRequest,
    authorization: str | None = Header(None),
):
    """
    Generate a marketing strategy from a high-level goal.

    This endpoint:
    1. Verifies Firebase ID token to authenticate the user
    2. Uses Gemini AI to generate a structured task list
    3. Creates a job in Firestore with status=pending_approval
    4. Returns the event_id for the user to review and approve

    The job remains in pending_approval until the user calls /approve.
    """
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

    # Verify token UID matches request UID
    if token_uid != request.uid:
        logger.warning(
            f"UID mismatch: token={token_uid}, request={request.uid}"
        )
        raise HTTPException(
            status_code=403,
            detail="UID mismatch between token and request",
        )

    try:
        # Generate unique event ID
        event_id = str(ULID())
        logger.info(f"Processing strategize request for user {request.uid}")

        # Generate task list via Gemini
        gemini_service = get_gemini_service()
        task_list = await gemini_service.generate_task_list(
            request.goal, request.target_platforms, request.brand_style
        )

        # Detect aspect ratio conflicts
        warnings = _detect_aspect_ratio_conflicts(request.target_platforms)

        # Create job in Firestore
        firestore_service = get_firestore_service()
        job = await firestore_service.create_job(event_id, request.uid, task_list)

        logger.info(
            f"Created job {event_id} for user {request.uid} "
            f"with status {job.status}"
        )

        return StrategizeResponse(
            event_id=event_id,
            status=job.status,
            task_list=task_list,
            message="Strategy generated successfully. Please review and approve.",
            warnings=warnings,
        )

    except Exception as e:
        logger.error(f"Error in strategize endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate strategy: {str(e)}",
        )
