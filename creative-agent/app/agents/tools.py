"""ADK tools for asset generation.

These are regular Python functions that ADK automatically wraps as tools.
The framework inspects function signatures, docstrings, and type hints to
generate tool schemas for the LLM.
"""

import json
import logging
from typing import Any

from promote_autonomy_shared.schemas import (
    CaptionTaskConfig,
    ImageTaskConfig,
    VideoTaskConfig,
    BrandStyle,
)

from app.services.copy import get_copy_service
from app.services.image import get_image_service
from app.services.video import get_video_service
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


async def generate_captions_tool(
    config: dict[str, Any],
    goal: str,
    event_id: str,
    brand_style: dict[str, Any] | None = None
) -> dict[str, str]:
    """Generate social media captions using Gemini and upload to Cloud Storage.

    Args:
        config: Caption configuration with keys 'n' (int) and 'style' (str)
        goal: Marketing goal for context
        event_id: Job ID for storage path
        brand_style: Optional brand style guidelines with keys 'tone', 'colors', 'tagline'

    Returns:
        Dict with captions_url key containing the Cloud Storage URL
    """
    try:
        logger.info(f"[ADK Tool] Generating captions for event {event_id}")

        # Validate 'n' parameter before passing to Pydantic (security hardening)
        if 'n' in config:
            n = config['n']
            if not isinstance(n, int) or n > 20 or n < 1:
                logger.error(f"[ADK Tool] Invalid n value: {n}")
                return {"error": f"n must be between 1 and 20 captions, got: {n}"}

        caption_config = CaptionTaskConfig(**config)
        copy_service = get_copy_service()
        storage_service = get_storage_service()

        # Parse brand style if provided
        brand_style_obj = BrandStyle(**brand_style) if brand_style else None

        # Generate captions
        captions = await copy_service.generate_captions(caption_config, goal, brand_style_obj)
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


async def generate_image_tool(
    config: dict[str, Any],
    event_id: str,
    brand_style: dict[str, Any] | None = None
) -> dict[str, str]:
    """Generate promotional images using Imagen and upload to Cloud Storage.

    Args:
        config: Image configuration with keys 'prompt', 'size', 'aspect_ratio', 'max_file_size_mb'
        event_id: Job ID for storage path
        brand_style: Optional brand style guidelines with keys 'tone', 'colors', 'tagline'

    Returns:
        Dict with image_url key containing the Cloud Storage URL
    """
    try:
        logger.info(f"[ADK Tool] Generating image for event {event_id}")

        # Validate max_file_size_mb before passing to Pydantic (security hardening)
        if 'max_file_size_mb' in config:
            max_size = config['max_file_size_mb']
            if not isinstance(max_size, (int, float)) or max_size > 100 or max_size < 0:
                logger.error(f"[ADK Tool] Invalid max_file_size_mb: {max_size}")
                return {"error": f"max_file_size_mb must be between 0 and 100 MB, got: {max_size}"}

        image_config = ImageTaskConfig(**config)
        image_service = get_image_service()
        storage_service = get_storage_service()

        # Parse brand style if provided
        brand_style_obj = BrandStyle(**brand_style) if brand_style else None

        # Generate image
        image_bytes = await image_service.generate_image(image_config, brand_style_obj)
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


async def generate_video_tool(
    config: dict[str, Any],
    event_id: str,
    brand_style: dict[str, Any] | None = None
) -> dict[str, str]:
    """Generate promotional videos using Veo and upload to Cloud Storage.

    Args:
        config: Video configuration with keys 'prompt', 'duration_sec', 'aspect_ratio', 'max_file_size_mb'
        event_id: Job ID for storage path
        brand_style: Optional brand style guidelines with keys 'tone', 'colors', 'tagline'

    Returns:
        Dict with video_url key, and optional 'warning' key if size exceeds limit
    """
    try:
        logger.info(f"[ADK Tool] Generating video for event {event_id}")

        # Validate max_file_size_mb before passing to Pydantic (security hardening)
        if 'max_file_size_mb' in config:
            max_size = config['max_file_size_mb']
            if not isinstance(max_size, (int, float)) or max_size > 500 or max_size < 0:
                logger.error(f"[ADK Tool] Invalid max_file_size_mb: {max_size}")
                return {"error": f"max_file_size_mb must be between 0 and 500 MB, got: {max_size}"}

        # Validate duration_sec
        if 'duration_sec' in config:
            duration = config['duration_sec']
            if not isinstance(duration, (int, float)) or duration > 60 or duration < 1:
                logger.error(f"[ADK Tool] Invalid duration_sec: {duration}")
                return {"error": f"duration_sec must be between 1 and 60 seconds, got: {duration}"}

        video_config = VideoTaskConfig(**config)
        video_service = get_video_service()
        storage_service = get_storage_service()

        # Parse brand style if provided
        brand_style_obj = BrandStyle(**brand_style) if brand_style else None

        # Generate video
        video_bytes = await video_service.generate_video(video_config, brand_style_obj)
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
