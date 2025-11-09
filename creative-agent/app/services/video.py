"""Video generation service."""

import asyncio
from typing import Protocol

from promote_autonomy_shared.schemas import VideoTaskConfig

from app.core.config import get_settings



class VideoService(Protocol):
    """Protocol for video generation services."""

    async def generate_video_brief(self, config: VideoTaskConfig) -> str:
        """Generate video script/brief.

        Args:
            config: Video generation configuration

        Returns:
            Video script or brief text
        """
        ...


class MockVideoService:
    """Mock video generation for testing."""

    async def generate_video_brief(self, config: VideoTaskConfig) -> str:
        """Generate mock video brief."""
        return f"""VIDEO BRIEF (MOCK)

Duration: {config.duration_sec} seconds
Prompt: {config.prompt}

Scene Breakdown:
- Opening (0-3s): Attention-grabbing hook
- Main Content (3-{config.duration_sec - 3}s): Core message
- Closing (last 3s): Call to action

Note: This is a mock video brief. In production, this would trigger Vertex AI Veo
for actual video generation or provide detailed shot-by-shot breakdown."""


class RealVideoService:
    """Real video brief generation using Gemini (Veo integration pending)."""

    def __init__(self):
        """Initialize Gemini for video brief generation."""
        try:
            import vertexai
            settings = get_settings()
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=settings.PROJECT_ID, location=settings.LOCATION)
            self.model = GenerativeModel("gemini-2.5-flash")
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Vertex AI for video service "
                f"(project={settings.PROJECT_ID}, location={settings.LOCATION}): {e}"
            ) from e

    async def generate_video_brief(self, config: VideoTaskConfig) -> str:
        """Generate detailed video brief using Gemini.

        Note: Vertex AI Veo integration will be added when API is available.
        For now, we return a detailed script that could be used for manual
        video production or future Veo integration.
        """
        prompt = f"""Create a detailed video production brief for a {config.duration_sec}-second marketing video.

Creative Direction:
{config.prompt}

Provide:
1. Scene-by-scene breakdown with timestamps
2. Visual descriptions for each scene
3. Suggested narration or on-screen text
4. Recommended music/audio style
5. Transitions between scenes

Format as a production-ready brief that a video editor could follow."""

        response = await asyncio.to_thread(self.model.generate_content, prompt)
        return response.text.strip()


# Service instance management
_mock_video_service: MockVideoService | None = None
_real_video_service: RealVideoService | None = None


def get_video_service() -> VideoService:
    """Get video service instance (singleton)."""
    global _mock_video_service, _real_video_service

    settings = get_settings()

    # Use mock if either USE_MOCK_VEO or USE_MOCK_GEMINI is enabled
    # RealVideoService uses Gemini, so respect USE_MOCK_GEMINI flag
    if settings.USE_MOCK_VEO or settings.USE_MOCK_GEMINI:
        if _mock_video_service is None:
            _mock_video_service = MockVideoService()
        return _mock_video_service
    else:
        if _real_video_service is None:
            _real_video_service = RealVideoService()
        return _real_video_service
