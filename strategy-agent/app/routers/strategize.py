"""Strategize endpoint - generate marketing strategy."""

import logging

from fastapi import APIRouter, Header, HTTPException, Form, File, UploadFile
from firebase_admin import auth
from ulid import ULID

from app.core.config import get_settings
from app.models.request import StrategizeRequest
from app.models.response import ErrorResponse, StrategizeResponse
from app.services.firestore import get_firestore_service
from app.services.gemini import get_gemini_service
from app.services.storage import get_storage_service
from promote_autonomy_shared.schemas import BrandStyle, JobStatus, Platform, PLATFORM_SPECS
import json

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
    goal: str = Form(..., min_length=10, max_length=500),
    target_platforms: str = Form(...),
    uid: str = Form(...),
    authorization: str | None = Header(None),
    reference_image: UploadFile | None = File(None),
    brand_style: str | None = Form(None),
):
    """
    Generate a marketing strategy from a high-level goal.

    This endpoint:
    1. Verifies Firebase ID token to authenticate the user
    2. Optionally uploads and analyzes reference product image
    3. Uses Gemini AI to generate a structured task list with optional brand style
    4. Creates a job in Firestore with status=pending_approval
    5. Returns the event_id for the user to review and approve

    The job remains in pending_approval until the user calls /approve.

    Args:
        goal: Marketing goal (10-500 characters)
        target_platforms: JSON array of platform strings
        uid: User ID from Firebase Auth
        reference_image: Optional product image (PNG/JPG, max 10MB)
        brand_style: Optional brand style JSON (colors, tone, tagline)
    """
    # Parse target_platforms from JSON string
    try:
        platforms_list = json.loads(target_platforms)
        if not platforms_list:
            raise HTTPException(
                status_code=400,
                detail="target_platforms must contain at least one platform",
            )
        platforms = [Platform(p) for p in platforms_list]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target_platforms format: {str(e)}",
        )

    # Parse brand_style from JSON string if provided
    brand_style_obj = None
    if brand_style:
        try:
            brand_style_dict = json.loads(brand_style)
            brand_style_obj = BrandStyle(**brand_style_dict)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid brand_style JSON: {str(e)}. Expected valid JSON with colors, tone, and optional tagline.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid brand_style: {str(e)}. Expected format: {{colors: [{{hex_code, name, usage}}], tone, tagline?}}",
            )

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
    if token_uid != uid:
        logger.warning(
            f"UID mismatch: token={token_uid}, request={uid}"
        )
        raise HTTPException(
            status_code=403,
            detail="UID mismatch between token and request",
        )

    # Initialize variables before try block to avoid UnboundLocalError in except handler
    reference_url = None
    reference_analysis = None

    try:
        # Generate unique event ID
        event_id = str(ULID())
        logger.info(f"Processing strategize request for user {uid}")

        # Get service instances once at the start
        storage_service = get_storage_service()
        gemini_service = get_gemini_service()

        if reference_image:
            # Validate file type
            if reference_image.content_type not in ["image/jpeg", "image/png"]:
                raise HTTPException(
                    status_code=400,
                    detail="Reference image must be JPEG or PNG",
                )

            # Read and validate file size
            content = await reference_image.read()
            settings = get_settings()
            max_size_bytes = settings.MAX_REFERENCE_IMAGE_SIZE_MB * 1024 * 1024
            if len(content) > max_size_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Reference image must be less than {settings.MAX_REFERENCE_IMAGE_SIZE_MB}MB",
                )

            # Validate actual file type using magic numbers (prevents Content-Type spoofing)
            import imghdr
            detected_type = imghdr.what(None, h=content[:32])
            if detected_type not in ["jpeg", "png"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image file. Detected type: {detected_type or 'unknown'}. Only JPEG and PNG images are supported.",
                )

            # Upload using already-read content (avoid double-read)
            reference_url = await storage_service.upload_reference_image(
                event_id=event_id,
                content=content,
                content_type=reference_image.content_type,
            )

            logger.info(f"Uploaded reference image to {reference_url}")

            try:
                # Analyze image with Gemini vision (pass actual MIME type)
                reference_analysis = await gemini_service.analyze_reference_image(
                    reference_url, goal, reference_image.content_type
                )

                logger.info(f"Generated image analysis: {reference_analysis[:100]}...")
            except Exception as analysis_error:
                # Clean up uploaded image if analysis fails
                logger.warning(f"Gemini vision analysis failed, cleaning up: {analysis_error}")
                try:
                    await storage_service.delete_reference_image(event_id)
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up reference image: {cleanup_error}")
                # Re-raise the original error
                raise

        # Generate task list via Gemini (with optional reference analysis and brand style)
        try:
            task_list = await gemini_service.generate_task_list(
                goal,
                platforms,
                brand_style=brand_style_obj,
                reference_analysis=reference_analysis
            )
        except Exception as task_list_error:
            # Clean up uploaded image if task list generation fails
            if reference_url:
                logger.warning(f"Task list generation failed, cleaning up reference image: {task_list_error}")
                try:
                    await storage_service.delete_reference_image(event_id)
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up reference image: {cleanup_error}")
            raise

        # Add reference_image_url to task_list if provided
        if reference_url:
            task_list.reference_image_url = reference_url
            # Also add to image task config if present
            if task_list.image:
                task_list.image.reference_image_url = reference_url

        # Detect aspect ratio conflicts
        warnings = _detect_aspect_ratio_conflicts(platforms)

        # Create job in Firestore
        firestore_service = get_firestore_service()
        job = await firestore_service.create_job(event_id, uid, task_list)

        # Note: reference_images will be populated during create_job from task_list.reference_image_url

        logger.info(
            f"Created job {event_id} for user {uid} "
            f"with status {job.status}"
        )

        return StrategizeResponse(
            event_id=event_id,
            status=job.status,
            task_list=task_list,
            message="Strategy generated successfully. Please review and approve.",
            warnings=warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up uploaded image if any step fails
        if reference_url:
            logger.warning(f"Strategize failed, cleaning up reference image: {e}")
            try:
                await storage_service.delete_reference_image(event_id)
                logger.info(f"Cleaned up reference image for failed job {event_id}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up reference image: {cleanup_error}")

        logger.error(f"Error in strategize endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate strategy: {str(e)}",
        )
