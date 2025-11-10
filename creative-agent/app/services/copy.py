"""Copy generation service."""

import asyncio
import re
from typing import Optional, Protocol

from promote_autonomy_shared.schemas import BrandStyle, CaptionTaskConfig

from app.core.config import get_settings


class CopyService(Protocol):
    """Protocol for copy generation services."""

    async def generate_captions(
        self,
        config: CaptionTaskConfig,
        goal: str,
        brand_style: Optional[BrandStyle] = None,
    ) -> list[str]:
        """Generate social media captions.

        Args:
            config: Caption generation configuration
            goal: Marketing goal for context
            brand_style: Brand style guide (optional)

        Returns:
            List of generated captions
        """
        ...


class MockCopyService:
    """Mock copy generation for testing."""

    async def generate_captions(
        self,
        config: CaptionTaskConfig,
        goal: str,
        brand_style: Optional[BrandStyle] = None,
    ) -> list[str]:
        """Generate mock captions based on goal keywords."""
        # Simple heuristic: use first three words from goal
        top_words = " ".join(goal.split()[:3])

        # Adjust emoji usage based on brand tone
        emoji = "✨"
        if brand_style:
            tone_emojis = {
                "professional": "",
                "casual": "👋",
                "playful": "🎉",
                "luxury": "✨",
                "technical": "⚙️",
            }
            emoji = tone_emojis.get(brand_style.tone, "✨")

        base_caption = f"{emoji} {top_words}" if emoji else top_words
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

        # Add tagline to first caption if provided
        if brand_style and brand_style.tagline and captions:
            captions[0] = f"{captions[0]} | {brand_style.tagline}"

        return captions


class RealCopyService:
    """Real copy generation using Gemini."""

    def __init__(self):
        """Initialize Gemini for copy generation."""
        import vertexai
        from vertexai.generative_models import GenerativeModel

        self.settings = get_settings()
        vertexai.init(project=self.settings.PROJECT_ID, location=self.settings.LOCATION)
        self.model = GenerativeModel("gemini-2.5-flash")

    async def generate_captions(
        self,
        config: CaptionTaskConfig,
        goal: str,
        brand_style: Optional[BrandStyle] = None,
    ) -> list[str]:
        """Generate captions using Gemini."""
        # Build brand context
        brand_context = ""
        if brand_style:
            tone_instructions = {
                "professional": "Use formal, corporate language. Avoid emojis.",
                "casual": "Use friendly, conversational tone. Emojis are okay.",
                "playful": "Be fun and energetic. Use emojis liberally.",
                "luxury": "Use sophisticated, elegant language. Minimal emojis.",
                "technical": "Be precise and detailed. Use industry terminology.",
            }
            tone_instruction = tone_instructions.get(
                brand_style.tone, "Use professional tone."
            )

            brand_context = f"""
Brand Guidelines:
- Tone: {brand_style.tone} - {tone_instruction}
- Tagline: {brand_style.tagline or "N/A"}

IMPORTANT: Include the tagline in at least one caption if provided.
"""

        prompt = f"""Generate {config.n} social media captions for this marketing goal:

Goal: {goal}
Style: {config.style}
{brand_context}

Requirements:
- Each caption should be engaging and on-brand
- Keep captions concise (under 280 characters)
- Include relevant emojis if appropriate for the style and tone
- Vary the approach across captions
- Match the specified brand tone

Return ONLY the captions, one per line, numbered 1-{config.n}."""

        # Add timeout to prevent infinite hangs
        response = await asyncio.wait_for(
            asyncio.to_thread(self.model.generate_content, prompt),
            timeout=self.settings.GEMINI_TIMEOUT_SEC
        )

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
