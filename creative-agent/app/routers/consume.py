"""Pub/Sub consumer endpoint for Creative Agent."""

import asyncio
import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel

from promote_autonomy_shared.schemas import TaskList, JobStatus

from app.core.config import get_settings
from app.services.copy import get_copy_service
from app.services.image import get_image_service
from app.services.video import get_video_service
from app.services.firestore import get_firestore_service
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


class PubSubMessage(BaseModel):
    """Pub/Sub push message format."""

    message: dict[str, Any]
    subscription: str


class MessageData(BaseModel):
    """Decoded message data."""

    event_id: str
    task_list: TaskList


@router.post("/consume")
async def consume_task(
    pubsub_message: PubSubMessage,
    request: Request,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Consume task from Pub/Sub and generate assets.

    This endpoint is called by Pub/Sub push subscription.
    It validates the OIDC token from Pub/Sub, decodes the message,
    generates all requested assets, and updates Firestore.
    """
    # Verify OIDC token from Pub/Sub
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split("Bearer ")[1]

    try:
        # The OIDC token from Pub/Sub has the full endpoint URL as audience
        # Cloud Run is behind a load balancer, so try both http and https
        audience_http = str(request.url)
        audience_https = audience_http.replace("http://", "https://", 1)

        # Try to verify with both audiences
        claim = None
        for aud in [audience_https, audience_http]:
            try:
                claim = id_token.verify_oauth2_token(
                    token, google_requests.Request(), aud
                )
                break
            except ValueError:
                continue

        if not claim:
            raise ValueError(f"Token has wrong audience, expected {audience_https}")

        # Verify the token is from the expected service account
        # TODO: Move this to configuration for multi-environment support
        expected_sa = "pubsub-invoker@promote-autonomy.iam.gserviceaccount.com"
        if claim.get("email") != expected_sa:
            logger.warning(f"Unexpected service account: {claim.get('email')}, expected: {expected_sa}")
            raise HTTPException(status_code=403, detail="Invalid service account")

    except HTTPException:
        # Re-raise HTTPExceptions (like the 403 above) without modification
        raise
    except Exception as e:
        # Catch token validation errors from id_token.verify_oauth2_token
        logger.warning("Invalid OIDC token: %s", e)
        raise HTTPException(status_code=401, detail="Invalid OIDC token") from e

    # Decode message data
    try:
        message_bytes = base64.b64decode(pubsub_message.message["data"])
        message_json = json.loads(message_bytes)
        message_data = MessageData(**message_json)
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid message format: {e}")

    event_id = message_data.event_id
    task_list = message_data.task_list

    # Get services
    firestore_service = get_firestore_service()
    storage_service = get_storage_service()
    copy_service = get_copy_service()
    image_service = get_image_service()
    video_service = get_video_service()

    # Verify job exists and is in processing state
    job = await firestore_service.get_job(event_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {event_id} not found")

    if job.status != JobStatus.PROCESSING:
        # Idempotent: if already completed, return success
        if job.status == JobStatus.COMPLETED:
            return {"status": "already_completed", "event_id": event_id}
        raise HTTPException(
            status_code=409,
            detail=f"Job {event_id} has invalid status: {job.status}",
        )

    try:
        # Define async functions for each asset type
        async def generate_captions_task():
            """Generate and upload captions."""
            if not task_list.captions:
                return None

            logger.info(f"Generating captions for job {event_id}")
            captions = await copy_service.generate_captions(task_list.captions, task_list.goal)
            captions_json = json.dumps(captions, indent=2).encode("utf-8")
            url = await storage_service.upload_file(
                event_id=event_id,
                filename="captions.json",
                content=captions_json,
                content_type="application/json",
            )
            logger.info(f"Captions generated for job {event_id}")
            return url

        async def generate_image_task():
            """Generate and upload image."""
            if not task_list.image:
                return None

            logger.info(f"Generating image for job {event_id}")
            image_bytes = await image_service.generate_image(task_list.image)
            url = await storage_service.upload_file(
                event_id=event_id,
                filename="image.png",
                content=image_bytes,
                content_type="image/png",
            )
            logger.info(f"Image generated for job {event_id}")
            return url

        async def generate_video_task():
            """Generate and upload video brief."""
            if not task_list.video:
                return None

            logger.info(f"Generating video brief for job {event_id}")
            video_brief = await video_service.generate_video_brief(task_list.video)
            brief_bytes = video_brief.encode("utf-8")
            url = await storage_service.upload_file(
                event_id=event_id,
                filename="video_brief.txt",
                content=brief_bytes,
                content_type="text/plain",
            )
            logger.info(f"Video brief generated for job {event_id}")
            return url

        # Generate all assets in parallel (2-3x faster)
        logger.info(f"Starting parallel asset generation for job {event_id}")
        captions_url, image_url, video_url = await asyncio.gather(
            generate_captions_task(),
            generate_image_task(),
            generate_video_task(),
        )
        logger.info(f"All assets generated for job {event_id}")

        # Mark job as completed with all asset URLs
        await firestore_service.update_job_status(
            event_id=event_id,
            status=JobStatus.COMPLETED,
            captions_url=captions_url,
            image_url=image_url,
            video_url=video_url,
        )
        logger.info(f"Job {event_id} completed successfully")

        # Build response outputs
        outputs = {}
        if captions_url:
            outputs["captions"] = captions_url
        if image_url:
            outputs["image"] = image_url
        if video_url:
            outputs["video"] = video_url

        return {"status": "success", "event_id": event_id, "outputs": outputs}

    except Exception as e:
        # Log error with full traceback
        logger.error(
            f"Asset generation failed for job {event_id}: {e}",
            exc_info=True
        )

        # Mark job as failed
        await firestore_service.update_job_status(
            event_id=event_id,
            status=JobStatus.FAILED,
        )

        # Return 200 to acknowledge message (prevent Pub/Sub retries)
        # The job is already marked as FAILED in Firestore
        return {
            "status": "failed",
            "event_id": event_id,
            "error": str(e)
        }
