"""Pub/Sub consumer endpoint for Creative Agent."""

import asyncio
import base64
import hashlib
import json
import logging
import re
from typing import Any, TYPE_CHECKING
from urllib.parse import urlparse

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

# Import types only during type checking to avoid circular imports
if TYPE_CHECKING:
    from app.services.firestore import FirestoreService
    from app.services.storage import StorageService
    from app.services.copy import CopyService
    from app.services.image import ImageService
    from app.services.video import VideoService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


class AdkOrchestrationError(Exception):
    """Exception raised when ADK orchestration fails and should fallback to legacy."""

    pass


class PubSubMessage(BaseModel):
    """Pub/Sub push message format."""

    message: dict[str, Any]
    subscription: str


class MessageData(BaseModel):
    """Decoded message data."""

    event_id: str
    task_list: TaskList


def should_use_adk(event_id: str) -> bool:
    """Determine if this job should use ADK orchestration.

    Uses deterministic hash of event_id for consistent behavior across retries.

    Args:
        event_id: Job identifier

    Returns:
        True if ADK should be used, False for legacy orchestration
    """
    if not settings.USE_ADK_ORCHESTRATION:
        return False

    # Deterministic selection based on event_id hash
    hash_val = int(hashlib.md5(event_id.encode()).hexdigest(), 16)
    return (hash_val % 100) < settings.ADK_ROLLOUT_PERCENTAGE


def _validate_gcs_url(url: str) -> bool:
    """Validate that a URL is a proper GCS URL from the expected bucket.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid and from expected bucket, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Verify it's HTTPS
        if parsed.scheme != 'https':
            logger.warning(f"URL is not HTTPS: {url}")
            return False

        # Verify it's from storage.googleapis.com
        if not parsed.netloc.endswith('storage.googleapis.com'):
            logger.warning(f"URL is not from storage.googleapis.com: {url}")
            return False

        # Verify path starts with expected bucket
        expected_bucket = settings.STORAGE_BUCKET
        if not parsed.path.startswith(f'/{expected_bucket}/'):
            logger.warning(
                f"URL not in expected GCS bucket '{expected_bucket}': {url}"
            )
            return False

        return True

    except Exception as e:
        logger.warning(f"Failed to parse URL '{url}': {e}")
        return False


def _extract_url_from_text(text: str, asset_type: str) -> str | None:
    """Extract and validate Cloud Storage URL from ADK text response.

    Args:
        text: ADK agent response text
        asset_type: Type of asset (captions, image, video)

    Returns:
        Extracted and validated URL or None if not found/invalid
    """
    # Look for patterns like "captions_url: https://..." or "captions_url": "https://..."
    patterns = [
        f'{asset_type}_url["\']?:\s*["\']?(https://storage\\.googleapis\\.com[^\\s"\']+)',
        f'{asset_type}_url["\']?\\s*=\\s*["\']?(https://storage\\.googleapis\\.com[^\\s"\']+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            url = match.group(1).rstrip('",\'')

            # Validate URL using helper function
            if _validate_gcs_url(url):
                return url

    return None


async def _generate_assets_with_adk(
    event_id: str,
    task_list: TaskList,
    firestore_service: "FirestoreService",
    storage_service: "StorageService",
) -> dict[str, str]:
    """Generate assets using ADK multi-agent orchestration.

    Args:
        event_id: Job identifier
        task_list: Task configuration
        firestore_service: Firestore service for storing warnings
        storage_service: Storage service for reference image cleanup

    Returns:
        Dict with keys: captions_url, image_url, video_url (as available)
    """
    # Lazy import ADK dependencies (only load when feature flag is enabled)
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from app.agents.coordinator import get_creative_coordinator

    logger.info(f"[ADK] Starting asset generation for job {event_id}")

    # Get ADK coordinator
    coordinator = get_creative_coordinator()

    # Prepare input for coordinator
    # Format as a structured prompt
    tasks_description = []

    if task_list.captions:
        tasks_description.append(
            f"1. Generate {task_list.captions.n} captions in '{task_list.captions.style}' style"
        )

    if task_list.image:
        tasks_description.append(
            f"2. Generate image: {task_list.image.prompt[:100]} "
            f"(size: {task_list.image.size}, aspect_ratio: {task_list.image.aspect_ratio})"
        )

    if task_list.video:
        tasks_description.append(
            f"3. Generate video: {task_list.video.prompt[:100]} "
            f"(duration: {task_list.video.duration_sec}s, aspect_ratio: {task_list.video.aspect_ratio})"
        )

    # Build brand context if available
    brand_context = ""
    if task_list.brand_style:
        brand_context = f"""
Brand Style Guidelines:
- Tone: {task_list.brand_style.tone}
- Colors: {', '.join(f"{c.name} (#{c.hex_code})" for c in task_list.brand_style.colors[:3])}
- Tagline: {task_list.brand_style.tagline or "N/A"}

IMPORTANT: Apply brand style consistently across all assets.
"""

    # Create prompt for coordinator
    prompt = f"""Generate creative assets for this marketing campaign:

Goal: {task_list.goal}
Target Platforms: {', '.join(p.value for p in task_list.target_platforms)}
Event ID: {event_id}
{brand_context}
Tasks to complete:
{chr(10).join(tasks_description)}

IMPORTANT:
- For captions: Use config={task_list.captions.model_dump() if task_list.captions else {}}
- For image: Use config={task_list.image.model_dump() if task_list.image else {}}
- For video: Use config={task_list.video.model_dump() if task_list.video else {}}

Delegate each task to the appropriate specialized agent (copy_writer, image_creator, video_producer).
Run all tasks in parallel for efficiency.

Return results in JSON format with URLs for all generated assets:
{{
  "captions_url": "https://storage.googleapis.com/...",
  "image_url": "https://storage.googleapis.com/...",
  "video_url": "https://storage.googleapis.com/..."
}}"""

    try:
        # Run ADK coordinator using Runner API
        # NOTE: We cannot use output_schema for structured responses because ADK has a
        # limitation: agents with tools (like our coordinator) cannot use output_schema.
        # See: https://github.com/google/adk-python/issues/701
        # Therefore, we must parse text responses manually.

        session_service = InMemorySessionService()
        runner = Runner(
            agent=coordinator,
            app_name="creative-agent",
            session_service=session_service
        )

        # Create content message for the agent
        user_message = types.Content(
            role='user',
            parts=[types.Part(text=prompt)]
        )

        # Execute agent and collect response
        # Why asyncio.to_thread: runner.run() is synchronous and blocks the event loop.
        # We wrap it in a thread to prevent blocking FastAPI's async event loop.
        # The runner.run() returns an iterator of events that we process to extract
        # the final response text from the LLM.
        def run_agent():
            events = runner.run(
                user_id="creative-agent",
                session_id=event_id,  # Use event_id as session_id for traceability
                new_message=user_message
            )
            # Collect final response from events
            for event in events:
                if event.is_final_response() and event.content:
                    return event.content.parts[0].text
            return ""  # Empty response if no final event

        result = await asyncio.to_thread(run_agent)

        logger.info(f"[ADK] Coordinator completed for job {event_id}")
        logger.debug(f"[ADK] Raw result: {result}")

        # Parse result - try to extract URLs from text response
        # Why multiple strategies: LLM output format is unpredictable. The agent may:
        # - Return valid JSON with extra text before/after
        # - Return JSON wrapped in markdown code blocks
        # - Return malformed JSON
        # We try progressively more lenient parsing strategies to maximize success rate.
        # This is necessary because output_schema is not available when using tools.
        outputs = {}

        # Try multiple JSON extraction strategies
        json_parsed = False

        # Strategy 1: Look for complete JSON object with balanced braces
        try:
            # Find JSON with proper nesting (handles multi-line)
            brace_count = 0
            start_idx = result.find('{')
            if start_idx != -1:
                for i, char in enumerate(result[start_idx:], start=start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = result[start_idx:i+1]
                            parsed = json.loads(json_str)

                            # Validate and extract URLs
                            for key in ["captions_url", "image_url", "video_url"]:
                                if key in parsed and isinstance(parsed[key], str):
                                    url = parsed[key].strip()
                                    if _validate_gcs_url(url):
                                        outputs[key] = url

                            json_parsed = True
                            break
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            logger.debug(f"[ADK] JSON extraction strategy 1 failed: {e}")

        # Strategy 2: Try markdown code block extraction
        if not json_parsed:
            try:
                code_block_match = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*\n?```', result, re.DOTALL)
                if code_block_match:
                    parsed = json.loads(code_block_match.group(1))
                    for key in ["captions_url", "image_url", "video_url"]:
                        if key in parsed and isinstance(parsed[key], str):
                            url = parsed[key].strip()
                            if _validate_gcs_url(url):
                                outputs[key] = url
                    json_parsed = True
            except (json.JSONDecodeError, AttributeError) as e:
                logger.debug(f"[ADK] JSON extraction strategy 2 failed: {e}")

        # Fallback: Regex extraction if JSON parsing failed
        if not json_parsed:
            logger.warning(f"[ADK] Failed to parse JSON from ADK response for job {event_id}, falling back to regex")
            if task_list.captions:
                url = _extract_url_from_text(result, "captions")
                if url:
                    outputs["captions_url"] = url

            if task_list.image:
                url = _extract_url_from_text(result, "image")
                if url:
                    outputs["image_url"] = url

            if task_list.video:
                url = _extract_url_from_text(result, "video")
                if url:
                    outputs["video_url"] = url

        # Check for warnings in result (especially for video size)
        if "warning" in result.lower():
            warning_match = re.search(r'"warning":\s*"([^"]+)"', result)
            if warning_match:
                warning_msg = warning_match.group(1)
                try:
                    await firestore_service.add_job_warning(event_id, warning_msg)
                    logger.warning(f"[ADK] Stored warning for job {event_id}: {warning_msg}")
                except Exception as e:
                    logger.error(f"[ADK] Failed to store warning for job {event_id}: {e}")

        # Delete reference image after successful completion
        if task_list.reference_image_url:
            try:
                await storage_service.delete_reference_image(event_id)
                logger.info(f"[ADK] Deleted reference image for job {event_id}")
            except Exception as e:
                # Log error but don't fail the job
                logger.warning(f"[ADK] Failed to delete reference image for job {event_id}: {e}")

        logger.info(f"[ADK] Asset generation completed for job {event_id}: {list(outputs.keys())}")
        return outputs

    except Exception as e:
        logger.error(f"[ADK] Asset generation failed for job {event_id}: {e}", exc_info=True)
        # Wrap in custom exception to signal fallback should occur
        raise AdkOrchestrationError(f"ADK orchestration failed: {e}") from e


async def _generate_assets_legacy(
    event_id: str,
    task_list: TaskList,
    firestore_service: "FirestoreService",
    storage_service: "StorageService",
    copy_service: "CopyService",
    image_service: "ImageService",
    video_service: "VideoService",
) -> dict[str, str]:
    """Generate assets using legacy asyncio.gather() orchestration.

    This is the current implementation, preserved for backward compatibility.

    Args:
        event_id: Job identifier
        task_list: Task configuration
        firestore_service: Firestore service
        storage_service: Storage service
        copy_service: Copy generation service
        image_service: Image generation service
        video_service: Video generation service

    Returns:
        Dict with keys: captions_url, image_url, video_url (as available)
    """
    # Define async functions for each asset type
    async def generate_captions_task():
        """Generate and upload captions."""
        if not task_list.captions:
            return None

        logger.info(f"[LEGACY] Generating captions for job {event_id}")
        captions = await copy_service.generate_captions(
            task_list.captions, task_list.goal, task_list.brand_style
        )
        captions_json = json.dumps(captions, indent=2).encode("utf-8")
        url = await storage_service.upload_file(
            event_id=event_id,
            filename="captions.json",
            content=captions_json,
            content_type="application/json",
        )
        logger.info(f"[LEGACY] Captions generated for job {event_id}")
        return url

    async def generate_image_task():
        """Generate and upload image."""
        if not task_list.image:
            return None

        logger.info(f"[LEGACY] Generating image for job {event_id}")
        image_bytes = await image_service.generate_image(
            task_list.image, task_list.brand_style
        )

        # Determine format based on compression
        if task_list.image.max_file_size_mb:
            filename = "image.jpg"
            content_type = "image/jpeg"
        else:
            filename = "image.png"
            content_type = "image/png"

        url = await storage_service.upload_file(
            event_id=event_id,
            filename=filename,
            content=image_bytes,
            content_type=content_type,
        )
        logger.info(f"[LEGACY] Image generated for job {event_id}")
        return url

    async def generate_video_task():
        """Generate and upload video."""
        if not task_list.video:
            return None

        logger.info(f"[LEGACY] Generating video for job {event_id}")
        video_bytes = await video_service.generate_video(
            task_list.video, task_list.brand_style
        )

        # Check if video exceeds size limit and store warning
        if task_list.video.max_file_size_mb:
            size_mb = len(video_bytes) / (1024 * 1024)
            if size_mb > task_list.video.max_file_size_mb:
                warning_msg = (
                    f"Generated video size ({size_mb:.2f} MB) exceeds "
                    f"platform limit ({task_list.video.max_file_size_mb} MB). "
                    f"This video may not upload successfully to the target platform."
                )
                try:
                    await firestore_service.add_job_warning(event_id, warning_msg)
                    logger.warning(f"[LEGACY] Stored warning for job {event_id}: {warning_msg}")
                except Exception as e:
                    logger.error(f"[LEGACY] Failed to store warning for job {event_id}: {e}")

        url = await storage_service.upload_file(
            event_id=event_id,
            filename="video.mp4",
            content=video_bytes,
            content_type="video/mp4",
        )
        logger.info(f"[LEGACY] Video generated for job {event_id}")
        return url

    # Generate all assets in parallel
    logger.info(f"[LEGACY] Starting parallel asset generation for job {event_id}")
    captions_url, image_url, video_url = await asyncio.gather(
        generate_captions_task(),
        generate_image_task(),
        generate_video_task(),
    )
    logger.info(f"[LEGACY] All assets generated for job {event_id}")

    # Delete reference image after successful completion
    if task_list.reference_image_url:
        try:
            await storage_service.delete_reference_image(event_id)
            logger.info(f"[LEGACY] Deleted reference image for job {event_id}")
        except Exception as e:
            # Log error but don't fail the job
            logger.warning(f"[LEGACY] Failed to delete reference image for job {event_id}: {e}")

    # Build outputs dict
    outputs = {}
    if captions_url:
        outputs["captions_url"] = captions_url
    if image_url:
        outputs["image_url"] = image_url
    if video_url:
        outputs["video_url"] = video_url

    return outputs


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
        expected_sa = settings.PUBSUB_SERVICE_ACCOUNT
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
        # FEATURE FLAG: Choose orchestration method
        use_adk = should_use_adk(event_id)

        try:
            if use_adk:
                logger.info(f"[ADK] Using ADK orchestration for job {event_id}")
                outputs = await _generate_assets_with_adk(
                    event_id=event_id,
                    task_list=task_list,
                    firestore_service=firestore_service,
                    storage_service=storage_service,
                )
            else:
                logger.info(f"[LEGACY] Using legacy orchestration for job {event_id}")
                outputs = await _generate_assets_legacy(
                    event_id=event_id,
                    task_list=task_list,
                    firestore_service=firestore_service,
                    storage_service=storage_service,
                    copy_service=copy_service,
                    image_service=image_service,
                    video_service=video_service,
                )
        except AdkOrchestrationError as adk_error:
            # ADK failed, fall back to legacy orchestration
            logger.warning(
                f"[ADK] Orchestration failed for job {event_id}, falling back to legacy: {adk_error}"
            )

            # Log ADK failure for monitoring
            try:
                await firestore_service.add_job_warning(
                    event_id,
                    f"ADK orchestration failed, used legacy fallback: {str(adk_error.__cause__)}"
                )
            except Exception as warn_error:
                logger.error(f"Failed to log ADK fallback warning: {warn_error}")

            # Fall back to legacy orchestration
            outputs = await _generate_assets_legacy(
                event_id=event_id,
                task_list=task_list,
                firestore_service=firestore_service,
                storage_service=storage_service,
                copy_service=copy_service,
                image_service=image_service,
                video_service=video_service,
            )

        # Mark job as completed with all asset URLs
        await firestore_service.update_job_status(
            event_id=event_id,
            status=JobStatus.COMPLETED,
            captions_url=outputs.get("captions_url"),
            image_url=outputs.get("image_url"),
            video_url=outputs.get("video_url"),
        )
        logger.info(f"Job {event_id} completed successfully")

        # Build response outputs (normalize key names)
        response_outputs = {}
        if outputs.get("captions_url"):
            response_outputs["captions"] = outputs["captions_url"]
        if outputs.get("image_url"):
            response_outputs["image"] = outputs["image_url"]
        if outputs.get("video_url"):
            response_outputs["video"] = outputs["video_url"]

        return {"status": "success", "event_id": event_id, "outputs": response_outputs}

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
