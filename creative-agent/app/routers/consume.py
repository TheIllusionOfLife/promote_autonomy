"""Pub/Sub consumer endpoint for Creative Agent."""

import base64
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from promote_autonomy_shared.schemas import TaskList, JobStatus

from app.core.config import get_settings
from app.services.copy import get_copy_service
from app.services.image import get_image_service
from app.services.video import get_video_service
from app.services.firestore import get_firestore_service
from app.services.storage import get_storage_service

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
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Consume task from Pub/Sub and generate assets.

    This endpoint is called by Pub/Sub push subscription.
    It validates the secret token, decodes the message,
    generates all requested assets, and updates Firestore.
    """
    # Verify secret token
    expected_token = f"Bearer {settings.PUBSUB_SECRET_TOKEN}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Invalid authorization token")

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

    captions_url = None
    image_url = None
    video_url = None

    try:
        # Generate captions if requested
        if task_list.captions:
            captions = await copy_service.generate_captions(task_list.captions, task_list.goal)

            # Upload captions as JSON
            captions_json = json.dumps(captions, indent=2).encode("utf-8")
            captions_url = await storage_service.upload_file(
                event_id=event_id,
                filename="captions.json",
                content=captions_json,
                content_type="application/json",
            )

        # Generate image if requested
        if task_list.image:
            image_bytes = await image_service.generate_image(task_list.image)

            image_url = await storage_service.upload_file(
                event_id=event_id,
                filename="image.png",
                content=image_bytes,
                content_type="image/png",
            )

        # Generate video brief if requested
        if task_list.video:
            video_brief = await video_service.generate_video_brief(task_list.video)

            # Upload brief as text file
            brief_bytes = video_brief.encode("utf-8")
            video_url = await storage_service.upload_file(
                event_id=event_id,
                filename="video_brief.txt",
                content=brief_bytes,
                content_type="text/plain",
            )

        # Update job to completed with asset URLs
        await firestore_service.update_job_status(
            event_id=event_id,
            status=JobStatus.COMPLETED,
            captions_url=captions_url,
            image_url=image_url,
            video_url=video_url,
        )

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
        # Mark job as failed
        await firestore_service.update_job_status(
            event_id=event_id,
            status=JobStatus.FAILED,
        )
        raise HTTPException(status_code=500, detail=f"Asset generation failed: {e}")
