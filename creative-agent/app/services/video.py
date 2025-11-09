"""Video generation service."""

import asyncio
import time
import struct
from typing import Protocol

from promote_autonomy_shared.schemas import VideoTaskConfig

from app.core.config import get_settings


class VideoService(Protocol):
    """Protocol for video generation services."""

    async def generate_video(self, config: VideoTaskConfig) -> bytes:
        """Generate video from prompt.

        Args:
            config: Video generation configuration

        Returns:
            Video bytes (MP4 format)
        """
        ...


class MockVideoService:
    """Mock video generation for testing."""

    async def generate_video(self, config: VideoTaskConfig) -> bytes:
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
        mvhd_data = b"\x00" * 100  # Minimal movie header
        mvhd_size = len(mvhd_data) + 8
        mvhd_box = struct.pack(">I", mvhd_size) + b"mvhd" + mvhd_data

        # moov container
        moov_content = mvhd_box
        moov_size = len(moov_content) + 8
        moov_box = struct.pack(">I", moov_size) + b"moov" + moov_content

        # mdat box (media data) - placeholder for actual video data
        mock_video_data = f"MOCK VIDEO - Duration: {config.duration_sec}s - Prompt: {config.prompt}".encode(
            "utf-8"
        )
        mdat_size = len(mock_video_data) + 8
        mdat_box = struct.pack(">I", mdat_size) + b"mdat" + mock_video_data

        # Combine all boxes
        mp4_bytes = ftyp_box + moov_box + mdat_box

        return mp4_bytes


class RealVeoVideoService:
    """Real video generation using Google Veo via google.genai SDK."""

    def __init__(self):
        """Initialize google.genai client for Veo video generation."""
        try:
            from google import genai
            from google.cloud import storage

            settings = get_settings()

            # Set environment variables required by google.genai
            import os

            os.environ["GOOGLE_CLOUD_PROJECT"] = settings.PROJECT_ID
            os.environ["GOOGLE_CLOUD_LOCATION"] = settings.LOCATION
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

            self.client = genai.Client()
            self.storage_client = storage.Client()

        except Exception as e:
            settings = get_settings()
            raise RuntimeError(
                f"Failed to initialize google.genai for Veo service "
                f"(project={settings.PROJECT_ID}, location={settings.LOCATION}): {e}"
            ) from e

    async def generate_video(self, config: VideoTaskConfig) -> bytes:
        """Generate video using Veo API with long-running operation polling.

        Args:
            config: Video generation configuration

        Returns:
            Video bytes (MP4 format) downloaded from GCS

        Raises:
            TimeoutError: If video generation exceeds configured timeout
            RuntimeError: If video generation fails
        """
        from google.genai.types import GenerateVideosConfig

        # Get current settings (allows for testing with mocked settings)
        settings = get_settings()

        # Determine aspect ratio based on common use cases
        # Default to 16:9 for landscape videos (most common for marketing)
        aspect_ratio = "16:9"

        # Determine duration (Veo 3 supports 4, 6, or 8 seconds)
        # Map requested duration to nearest supported value
        if config.duration_sec <= 5:
            duration = 4
        elif config.duration_sec <= 7:
            duration = 6
        else:
            duration = 8

        # Prepare GCS output URI
        if not settings.VIDEO_OUTPUT_GCS_BUCKET:
            raise ValueError(
                "VIDEO_OUTPUT_GCS_BUCKET must be configured for Veo video generation. "
                "Example: gs://your-bucket/veo-output"
            )

        output_gcs_uri = settings.VIDEO_OUTPUT_GCS_BUCKET

        # Start video generation operation
        operation = await asyncio.to_thread(
            self.client.models.generate_videos,
            model=settings.VEO_MODEL,
            prompt=config.prompt,
            config=GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
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

        # Extract video URI from result
        if not operation.result or not operation.result.generated_videos:
            raise RuntimeError("Veo API returned no videos in operation result")

        video_uri = operation.result.generated_videos[0].video.uri

        # Download video from GCS
        video_bytes = await self._download_from_gcs(video_uri)

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

        # Remove 'gs://' prefix
        path = gcs_uri[5:]

        # Split into bucket and object path
        parts = path.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid GCS URI format: {gcs_uri}. Must be gs://bucket/path")

        bucket_name = parts[0]
        object_path = parts[1]

        # Download from GCS
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(object_path)

        video_bytes = await asyncio.to_thread(blob.download_as_bytes)

        return video_bytes


# Service instance management (singleton pattern)
_mock_video_service: MockVideoService | None = None
_real_video_service: RealVeoVideoService | None = None


def get_video_service() -> VideoService:
    """Get video service instance (singleton).

    Returns:
        MockVideoService if USE_MOCK_VEO or USE_MOCK_GEMINI is True,
        otherwise RealVeoVideoService.
    """
    global _mock_video_service, _real_video_service

    settings = get_settings()

    # Use mock if either flag is enabled
    if settings.USE_MOCK_VEO or settings.USE_MOCK_GEMINI:
        if _mock_video_service is None:
            _mock_video_service = MockVideoService()
        return _mock_video_service
    else:
        if _real_video_service is None:
            _real_video_service = RealVeoVideoService()
        return _real_video_service
