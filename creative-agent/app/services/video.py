"""Video generation service."""

import asyncio
import logging
import time
import struct
from typing import Optional, Protocol

from promote_autonomy_shared.schemas import BrandStyle, VideoTaskConfig

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VideoService(Protocol):
    """Protocol for video generation services."""

    async def generate_video(
        self, config: VideoTaskConfig, brand_style: Optional[BrandStyle] = None
    ) -> bytes:
        """Generate video from prompt.

        Args:
            config: Video generation configuration
            brand_style: Brand style guide (optional)

        Returns:
            Video bytes (MP4 format)
        """
        ...


class MockVideoService:
    """Mock video generation for testing."""

    # Mock MP4 structure constants
    MOCK_MVHD_HEADER_SIZE = 100  # Minimal header size sufficient for MP4 parsers

    async def generate_video(
        self, config: VideoTaskConfig, brand_style: Optional[BrandStyle] = None
    ) -> bytes:
        """Generate minimal valid MP4 file with placeholder content.

        Creates a very basic MP4 file structure that can be recognized
        as a valid video file by parsers and players.
        """
        # Create minimal MP4 structure
        # MP4 consists of boxes/atoms with format: [size:4 bytes][type:4 bytes][data]

        # ftyp box (file type) - required for MP4
        ftyp_data = b"isom\x00\x00\x02\x00isomiso2mp41"
        ftyp_size = len(ftyp_data) + 8
        ftyp_box = struct.pack(">I", ftyp_size) + b"ftyp" + ftyp_data

        # moov box (movie metadata) - container for track info
        # For mock, we'll create a minimal moov box structure
        mvhd_data = b"\x00" * self.MOCK_MVHD_HEADER_SIZE
        mvhd_size = len(mvhd_data) + 8
        mvhd_box = struct.pack(">I", mvhd_size) + b"mvhd" + mvhd_data

        # moov container
        moov_content = mvhd_box
        moov_size = len(moov_content) + 8
        moov_box = struct.pack(">I", moov_size) + b"moov" + moov_content

        # mdat box (media data) - placeholder for actual video data
        # Include brand info if provided
        brand_info = ""
        if brand_style:
            brand_info = f" - Brand: {brand_style.tone}"
        mock_video_data = f"MOCK VIDEO - Duration: {config.duration_sec}s{brand_info} - Prompt: {config.prompt}".encode(
            "utf-8"
        )
        mdat_size = len(mock_video_data) + 8
        mdat_box = struct.pack(">I", mdat_size) + b"mdat" + mock_video_data

        # Combine all boxes
        mp4_bytes = ftyp_box + moov_box + mdat_box

        return mp4_bytes


class RealVeoVideoService:
    """Real video generation using Google Veo via google.genai SDK."""

    # Class-level constants to avoid recreation on every call
    TONE_DESCRIPTORS = {
        "professional": "clean, corporate aesthetic",
        "casual": "friendly, approachable vibe",
        "playful": "energetic, fun atmosphere",
        "luxury": "elegant, sophisticated feel",
        "technical": "precise, detailed style",
    }

    def __init__(self):
        """Initialize google.genai client for Veo video generation."""
        settings = get_settings()

        # Validate required configuration
        if not settings.VIDEO_OUTPUT_GCS_BUCKET:
            raise ValueError(
                "VIDEO_OUTPUT_GCS_BUCKET is required for real VEO video generation. "
                "Example: gs://your-bucket/veo-output"
            )

        # Warn if location is not us-central1 (VEO 3.0 requirement)
        if settings.LOCATION != "us-central1":
            logger.warning(
                f"VEO 3.0 is only available in us-central1. "
                f"Current LOCATION is '{settings.LOCATION}'. "
                f"Video generation will fail unless LOCATION is changed to us-central1."
            )

        try:
            from google import genai
            from google.cloud import storage

            # Set environment variables required by google.genai
            import os

            os.environ["GOOGLE_CLOUD_PROJECT"] = settings.PROJECT_ID
            os.environ["GOOGLE_CLOUD_LOCATION"] = settings.LOCATION
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

            self.client = genai.Client()
            self.storage_client = storage.Client()

        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize google.genai for Veo service "
                f"(project={settings.PROJECT_ID}, location={settings.LOCATION}): {e}"
            ) from e

    async def generate_video(
        self, config: VideoTaskConfig, brand_style: Optional[BrandStyle] = None
    ) -> bytes:
        """Generate video using Veo API with long-running operation polling.

        Args:
            config: Video generation configuration
            brand_style: Brand style guide (optional)

        Returns:
            Video bytes (MP4 format) downloaded from GCS

        Raises:
            ValueError: If prompt is too long or invalid
            TimeoutError: If video generation exceeds configured timeout
            RuntimeError: If video generation fails
        """
        from google.genai.types import GenerateVideosConfig

        # Enhance prompt with brand context
        enhanced_prompt = config.prompt
        if brand_style:
            tone_desc = self.TONE_DESCRIPTORS.get(brand_style.tone, "professional style")
            enhanced_prompt = f"{config.prompt}. Style: {tone_desc}."

            if brand_style.colors:
                # Find primary color, fallback to first if no primary specified
                primary_color = next(
                    (c for c in brand_style.colors if c.usage == "primary"),
                    brand_style.colors[0]
                )
                enhanced_prompt += f" Use {primary_color.name} (#{primary_color.hex_code}) as primary color accent."

        # Validate prompt length to prevent abuse and API errors
        MAX_PROMPT_LENGTH = 10000  # Reasonable limit for VEO prompts
        if len(enhanced_prompt) > MAX_PROMPT_LENGTH:
            raise ValueError(
                f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters "
                f"(got {len(enhanced_prompt)})"
            )

        # Get current settings (allows for testing with mocked settings)
        settings = get_settings()

        # Use explicit aspect_ratio if provided, otherwise default to 16:9
        aspect_ratio = config.aspect_ratio if config.aspect_ratio else "16:9"

        # Determine duration (Veo 3 supports 4, 6, or 8 seconds)
        # Map requested duration to nearest supported value
        if config.duration_sec <= 5:
            duration = 4
        elif config.duration_sec <= 7:
            duration = 6
        else:
            duration = 8

        if duration != config.duration_sec:
            logger.info(
                f"Mapping requested duration {config.duration_sec}s to VEO-supported {duration}s "
                f"(VEO 3.0 only supports 4, 6, or 8 seconds)"
            )

        # Use GCS output URI from settings (validated in __init__)
        output_gcs_uri = settings.VIDEO_OUTPUT_GCS_BUCKET

        # Start video generation operation
        operation = await asyncio.to_thread(
            self.client.models.generate_videos,
            model=settings.VEO_MODEL,
            prompt=enhanced_prompt,
            config=GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                duration_seconds=duration,
                output_gcs_uri=output_gcs_uri,
            ),
        )

        # Poll operation until complete with timeout
        start_time = time.time()
        while operation.done is not True:  # Handle None and False
            elapsed = time.time() - start_time
            if elapsed > settings.VEO_TIMEOUT_SEC:
                raise TimeoutError(
                    f"Video generation timed out after {settings.VEO_TIMEOUT_SEC} seconds. "
                    f"Veo typically takes 2-5 minutes per video."
                )

            await asyncio.sleep(settings.VEO_POLLING_INTERVAL_SEC)

            # Refresh operation status
            operation = await asyncio.to_thread(self.client.operations.get, operation)

        # Check for errors first before inspecting result
        if hasattr(operation, 'error') and operation.error:
            error_msg = f"Veo API error: {operation.error}"
            if hasattr(operation.error, 'message'):
                error_msg = f"Veo API error: {operation.error.message}"
            if hasattr(operation.error, 'code'):
                error_msg = f"{error_msg} (code: {operation.error.code})"
            raise RuntimeError(error_msg)

        # Extract video URI from result
        if not operation.result or not operation.result.generated_videos:
            raise RuntimeError("Veo API returned no videos in operation result")

        video_uri = operation.result.generated_videos[0].video.uri

        # Download video from GCS
        video_bytes = await self._download_from_gcs(video_uri)

        # Note: File size validation is performed in consume.py after generation
        # to store warnings in Firestore for user visibility. The video service
        # focuses solely on video generation and download.

        return video_bytes

    async def _download_from_gcs(self, gcs_uri: str) -> bytes:
        """Download video bytes from Google Cloud Storage.

        Args:
            gcs_uri: GCS URI in format gs://bucket-name/path/to/file.mp4

        Returns:
            Video file bytes

        Raises:
            ValueError: If URI format is invalid
        """
        # Parse GCS URI: gs://bucket-name/path/to/file
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}. Must start with 'gs://'")

        # Remove 'gs://' prefix using modern Python 3.9+ method
        path = gcs_uri.removeprefix("gs://")

        # Split into bucket and object path
        parts = path.split("/", 1)
        if len(parts) != 2 or not parts[1]:
            raise ValueError(
                f"Invalid GCS URI format: {gcs_uri}. "
                f"Must be gs://bucket/object-path (bucket-only URIs not supported)"
            )

        bucket_name = parts[0]
        object_path = parts[1]

        # Download from GCS
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(object_path)
            video_bytes = await asyncio.to_thread(blob.download_as_bytes)
            return video_bytes
        except Exception as e:
            # Import here to avoid dependency in mock mode
            from google.api_core import exceptions as gcp_exceptions

            if isinstance(e, gcp_exceptions.NotFound):
                raise RuntimeError(f"Video not found at {gcs_uri}. VEO may have failed to write output.") from e
            elif isinstance(e, gcp_exceptions.Forbidden):
                raise RuntimeError(f"Permission denied accessing {gcs_uri}. Check service account IAM roles.") from e
            else:
                raise RuntimeError(f"Failed to download video from {gcs_uri}: {e}") from e


# Service instance management (singleton pattern)
_mock_video_service: MockVideoService | None = None
_real_video_service: RealVeoVideoService | None = None


def get_video_service() -> VideoService:
    """Get video service instance (singleton).

    Returns:
        MockVideoService if USE_MOCK_VEO is True,
        otherwise RealVeoVideoService.
    """
    global _mock_video_service, _real_video_service

    settings = get_settings()

    # Use mock video service when flag is enabled
    if settings.USE_MOCK_VEO:
        if _mock_video_service is None:
            _mock_video_service = MockVideoService()
        return _mock_video_service
    else:
        if _real_video_service is None:
            _real_video_service = RealVeoVideoService()
        return _real_video_service
