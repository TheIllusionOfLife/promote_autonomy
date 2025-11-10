"""ADK tools for asset generation."""

import json
import logging
from typing import Any

from google.adk.tools import Tool
from promote_autonomy_shared.schemas import (
    CaptionTaskConfig,
    ImageTaskConfig,
    VideoTaskConfig,
)

from app.services.copy import get_copy_service
from app.services.image import get_image_service
from app.services.video import get_video_service
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


@Tool(description="Generate social media captions using Gemini")
async def generate_captions_tool(
    config: dict[str, Any],
    goal: str,
    event_id: str
) -> dict[str, str]:
    """Generate captions and upload to Cloud Storage.

    Args:
        config: Caption configuration with keys 'n' (int) and 'style' (str)
        goal: Marketing goal for context
        event_id: Job ID for storage path

    Returns:
        Dict with captions_url key containing the Cloud Storage URL
    """
    try:
        logger.info(f"[ADK Tool] Generating captions for event {event_id}")

        caption_config = CaptionTaskConfig(**config)
        copy_service = get_copy_service()
        storage_service = get_storage_service()

        # Generate captions
        captions = await copy_service.generate_captions(caption_config, goal)
        logger.info(f"[ADK Tool] Generated {len(captions)} captions for event {event_id}")

        # Upload to storage
        captions_json = json.dumps(captions, indent=2).encode("utf-8")
        url = await storage_service.upload_file(
            event_id=event_id,
            filename="captions.json",
            content=captions_json,
            content_type="application/json",
        )

        logger.info(f"[ADK Tool] Uploaded captions to {url}")
        return {"captions_url": url}

    except Exception as e:
        logger.error(f"[ADK Tool] Caption generation failed for event {event_id}: {e}", exc_info=True)
        return {"error": f"Caption generation failed: {str(e)}"}


@Tool(description="Generate promotional images using Imagen")
async def generate_image_tool(
    config: dict[str, Any],
    event_id: str
) -> dict[str, str]:
    """Generate image and upload to Cloud Storage.

    Args:
        config: Image configuration with keys 'prompt', 'size', 'aspect_ratio', 'max_file_size_mb'
        event_id: Job ID for storage path

    Returns:
        Dict with image_url key containing the Cloud Storage URL
    """
    try:
        logger.info(f"[ADK Tool] Generating image for event {event_id}")

        image_config = ImageTaskConfig(**config)
        image_service = get_image_service()
        storage_service = get_storage_service()

        # Generate image
        image_bytes = await image_service.generate_image(image_config)
        logger.info(f"[ADK Tool] Generated image ({len(image_bytes)} bytes) for event {event_id}")

        # Determine format based on compression
        if image_config.max_file_size_mb:
            filename = "image.jpg"
            content_type = "image/jpeg"
        else:
            filename = "image.png"
            content_type = "image/png"

        # Upload to storage
        url = await storage_service.upload_file(
            event_id=event_id,
            filename=filename,
            content=image_bytes,
            content_type=content_type,
        )

        logger.info(f"[ADK Tool] Uploaded image to {url}")
        return {"image_url": url}

    except Exception as e:
        logger.error(f"[ADK Tool] Image generation failed for event {event_id}: {e}", exc_info=True)
        return {"error": f"Image generation failed: {str(e)}"}


@Tool(description="Generate promotional videos using Veo")
async def generate_video_tool(
    config: dict[str, Any],
    event_id: str
) -> dict[str, str]:
    """Generate video and upload to Cloud Storage.

    Args:
        config: Video configuration with keys 'prompt', 'duration_sec', 'aspect_ratio', 'max_file_size_mb'
        event_id: Job ID for storage path

    Returns:
        Dict with video_url key, and optional 'warning' key if size exceeds limit
    """
    try:
        logger.info(f"[ADK Tool] Generating video for event {event_id}")

        video_config = VideoTaskConfig(**config)
        video_service = get_video_service()
        storage_service = get_storage_service()

        # Generate video
        video_bytes = await video_service.generate_video(video_config)
        logger.info(f"[ADK Tool] Generated video ({len(video_bytes)} bytes) for event {event_id}")

        # Check size and create warning if needed
        warning = None
        if video_config.max_file_size_mb:
            size_mb = len(video_bytes) / (1024 * 1024)
            if size_mb > video_config.max_file_size_mb:
                warning = (
                    f"Generated video size ({size_mb:.2f} MB) exceeds "
                    f"platform limit ({video_config.max_file_size_mb} MB). "
                    f"This video may not upload successfully to the target platform."
                )
                logger.warning(f"[ADK Tool] {warning}")

        # Upload to storage
        url = await storage_service.upload_file(
            event_id=event_id,
            filename="video.mp4",
            content=video_bytes,
            content_type="video/mp4",
        )

        logger.info(f"[ADK Tool] Uploaded video to {url}")

        result = {"video_url": url}
        if warning:
            result["warning"] = warning
        return result

    except Exception as e:
        logger.error(f"[ADK Tool] Video generation failed for event {event_id}: {e}", exc_info=True)
        return {"error": f"Video generation failed: {str(e)}"}
