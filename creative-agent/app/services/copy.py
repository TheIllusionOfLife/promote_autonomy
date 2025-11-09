"""Copy generation service."""

import asyncio
import re
from typing import Protocol

from promote_autonomy_shared.schemas import CaptionTaskConfig

from app.core.config import get_settings


class CopyService(Protocol):
    """Protocol for copy generation services."""

    async def generate_captions(self, config: CaptionTaskConfig, goal: str) -> list[str]:
        """Generate social media captions.

        Args:
            config: Caption generation configuration
            goal: Marketing goal for context

        Returns:
            List of generated captions
        """
        ...


class MockCopyService:
    """Mock copy generation for testing."""

    async def generate_captions(self, config: CaptionTaskConfig, goal: str) -> list[str]:
        """Generate mock captions based on goal keywords."""
        # Simple heuristic: use first three words from goal
        top_words = " ".join(goal.split()[:3])
        base_caption = f"✨ {top_words}"
        captions = []

        for i in range(config.n):
            if config.style.lower() == "professional":
                captions.append(f"{base_caption} - Professional insight #{i + 1}")
            elif config.style.lower() == "casual":
                captions.append(f"{base_caption} 🎉 Casual vibe #{i + 1}")
            elif config.style.lower() == "humorous":
                captions.append(f"{base_caption} 😂 Funny take #{i + 1}")
            else:
                captions.append(f"{base_caption} - Caption #{i + 1}")

        return captions


class RealCopyService:
    """Real copy generation using Gemini."""

    def __init__(self):
        """Initialize Gemini for copy generation."""
        import vertexai
        from vertexai.generative_models import GenerativeModel

        settings = get_settings()
        vertexai.init(project=settings.PROJECT_ID, location=settings.LOCATION)
        self.model = GenerativeModel("gemini-2.5-flash")

    async def generate_captions(self, config: CaptionTaskConfig, goal: str) -> list[str]:
        """Generate captions using Gemini."""
        prompt = f"""Generate {config.n} social media captions for this marketing goal:

Goal: {goal}
Style: {config.style}

Requirements:
- Each caption should be engaging and on-brand
- Keep captions concise (under 280 characters)
- Include relevant emojis if appropriate for the style
- Vary the approach across captions

Return ONLY the captions, one per line, numbered 1-{config.n}."""

        response = await asyncio.to_thread(self.model.generate_content, prompt)

        # Parse numbered list using regex for robustness
        # Handles formats: "1. ", "1) ", "1- ", "1.", "1)", "1 ", etc.
        lines = response.text.strip().split("\n")
        captions = []
        for line in lines:
            # Remove leading numbering (e.g., "1. ", "1) ", "1-", "1 ")
            clean_line = re.sub(r"^\s*\d+[\.\)\-\s]\s*", "", line.strip())
            if clean_line:
                captions.append(clean_line)

        return captions[:config.n]


# Service instance management
_mock_copy_service: MockCopyService | None = None
_real_copy_service: RealCopyService | None = None


def get_copy_service() -> CopyService:
    """Get copy service instance (singleton)."""
    global _mock_copy_service, _real_copy_service

    settings = get_settings()

    if settings.USE_MOCK_GEMINI:
        if _mock_copy_service is None:
            _mock_copy_service = MockCopyService()
        return _mock_copy_service
    else:
        if _real_copy_service is None:
            _real_copy_service = RealCopyService()
        return _real_copy_service
