"""Gemini API service for task list generation."""

import asyncio
import json
import logging
import re
from typing import Optional, Protocol

from promote_autonomy_shared.schemas import (
    BrandStyle,
    CaptionTaskConfig,
    ImageTaskConfig,
    Platform,
    PLATFORM_SPECS,
    TaskList,
    VideoTaskConfig,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiService(Protocol):
    """Protocol for Gemini service implementations."""

    async def generate_task_list(
        self, goal: str, target_platforms: list[Platform], brand_style: Optional[BrandStyle] = None
    ) -> TaskList:
        """Generate a task list from a marketing goal."""
        ...


class MockGeminiService:
    """Mock implementation for development without real API."""

    async def generate_task_list(
        self, goal: str, target_platforms: list[Platform], brand_style: Optional[BrandStyle] = None
    ) -> TaskList:
        """Generate a mock task list based on the goal and target platforms."""
        brand_info = ""
        if brand_style:
            colors = ", ".join([c.name for c in brand_style.colors])
            brand_info = f" with {brand_style.tone} tone and colors: {colors}"
        logger.info(f"[MOCK] Generating task list for goal: {goal}, platforms: {target_platforms}{brand_info}")

        # Calculate platform constraints (most restrictive wins)
        specs = [PLATFORM_SPECS[p] for p in target_platforms]

        # Image constraints
        min_image_size_mb = min(s.max_image_size_mb for s in specs)
        # Use the first platform's aspect ratio (or most common if needed)
        image_aspect_ratio = specs[0].image_aspect_ratio
        image_size = specs[0].image_size

        # Video constraints
        min_video_duration = min(s.max_video_length_sec for s in specs)
        min_video_size_mb = min(s.max_video_size_mb for s in specs)
        video_aspect_ratio = specs[0].video_aspect_ratio

        # Simple heuristic: generate different tasks based on goal keywords
        has_social = any(
            word in goal.lower() for word in ["twitter", "social", "post", "tweet"]
        )
        has_image = any(
            word in goal.lower()
            for word in ["visual", "image", "graphic", "picture", "photo"]
        )
        has_video = any(
            word in goal.lower()
            for word in ["video", "demo", "tutorial", "campaign"]
        )

        task_list = TaskList(
            goal=goal,
            target_platforms=target_platforms,
            brand_style=brand_style,
            captions=CaptionTaskConfig(
                n=5 if has_social else 3,
                style="twitter" if has_social else "engaging",
            ),
            image=ImageTaskConfig(
                prompt=f"Modern promotional visual for: {goal[:50]}",
                size=image_size,
                aspect_ratio=image_aspect_ratio,
                max_file_size_mb=min_image_size_mb,
            )
            if has_image or len(goal) > 30
            else None,
            video=VideoTaskConfig(
                prompt=f"Promotional video for: {goal[:50]}",
                duration_sec=min_video_duration,  # Use most restrictive duration
                aspect_ratio=video_aspect_ratio,
                max_file_size_mb=min_video_size_mb,
            )
            if has_video
            else None,
        )

        logger.info(f"[MOCK] Generated task list: {task_list.model_dump_json()}")
        return task_list


class RealGeminiService:
    """Real Gemini API implementation."""

    # Class-level constants to avoid recreation on every call
    TONE_DESCRIPTIONS = {
        "professional": "corporate, formal language; avoid emojis",
        "casual": "friendly, conversational tone; emojis are okay",
        "playful": "fun and energetic; use emojis liberally",
        "luxury": "sophisticated, elegant language; minimal emojis",
        "technical": "precise and detailed; use industry terminology",
    }

    def __init__(self):
        """Initialize Gemini client."""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(project=settings.PROJECT_ID, location=settings.LOCATION)
            self.model = GenerativeModel(settings.GEMINI_MODEL)
            logger.info(
                f"Initialized Gemini model: {settings.GEMINI_MODEL} "
                f"in {settings.LOCATION}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    async def generate_task_list(
        self, goal: str, target_platforms: list[Platform], brand_style: Optional[BrandStyle] = None
    ) -> TaskList:
        """Generate a task list using Gemini API."""
        # Calculate platform constraints
        specs = [PLATFORM_SPECS[p] for p in target_platforms]

        # Image constraints
        min_image_size_mb = min(s.max_image_size_mb for s in specs)
        image_aspect_ratio = specs[0].image_aspect_ratio
        image_size = specs[0].image_size

        # Video constraints
        min_video_duration = min(s.max_video_length_sec for s in specs)
        min_video_size_mb = min(s.max_video_size_mb for s in specs)
        video_aspect_ratio = specs[0].video_aspect_ratio

        # Caption constraints
        min_caption_length = min(s.caption_max_length for s in specs)

        platform_names = ", ".join([p.value for p in target_platforms])

        # Build brand context for prompt
        brand_context = ""
        if brand_style:
            color_list = ", ".join(
                [f"{c.name} (#{c.hex_code})" for c in brand_style.colors]
            )
            tone_desc = self.TONE_DESCRIPTIONS.get(
                brand_style.tone, "professional tone"
            )

            brand_context = f"""
Brand Style Requirements:
- Brand Colors: {color_list}
- Brand Tone: {brand_style.tone} ({tone_desc})
- Brand Tagline: {brand_style.tagline or "N/A"}

IMPORTANT: All generated content MUST:
1. Reference the specified brand colors in image and video prompts
2. Match the {brand_style.tone} tone in all captions
3. Include the tagline in at least one caption if provided
"""

        prompt = f"""You are a marketing strategist AI. Given a marketing goal and target platforms, generate a structured task list.

Marketing Goal: {goal}
Target Platforms: {platform_names}

Platform Constraints:
- Image: {image_size} ({image_aspect_ratio}), max {min_image_size_mb}MB
- Video: {video_aspect_ratio}, max {min_video_duration}s, max {min_video_size_mb}MB
- Captions: max {min_caption_length} characters each
{brand_context}
Generate a JSON object with this structure:
{{
  "goal": "<the goal>",
  "target_platforms": {[p.value for p in target_platforms]},
  "captions": {{"n": <1-10>, "style": "<engaging|twitter|linkedin>"}},
  "image": {{"prompt": "<image description>", "size": "{image_size}", "aspect_ratio": "{image_aspect_ratio}", "max_file_size_mb": {min_image_size_mb}}} or null,
  "video": {{"prompt": "<video description>", "duration_sec": <5-{min_video_duration}>, "aspect_ratio": "{video_aspect_ratio}", "max_file_size_mb": {min_video_size_mb}}} or null
}}

Rules:
- Always include captions (1-10 captions)
- Include image if goal mentions visuals or is substantial
- Include video only if explicitly mentioned or goal is major campaign
- Be specific and actionable in prompts
- Ensure image/video specs match platform constraints above
- Image and video prompts should reference brand colors when provided
- Return ONLY valid JSON, no markdown formatting
"""

        try:
            # Add timeout to prevent infinite hangs
            response = await asyncio.wait_for(
                asyncio.to_thread(self.model.generate_content, prompt),
                timeout=settings.GEMINI_TIMEOUT_SEC
            )
            response_text = response.text.strip()

            # Extract JSON from markdown code blocks using regex
            # Handles formats: ```json\n{...}\n```, ```\n{...}\n```, or plain {...}
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1).strip()

            # Parse JSON to TaskList
            data = json.loads(response_text)
            # Add brand_style to the parsed data
            data["brand_style"] = brand_style.model_dump() if brand_style else None
            task_list = TaskList(**data)

            logger.info(f"Generated task list via Gemini: {task_list.model_dump_json()}")
            return task_list

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Fallback to basic task list
            logger.warning("Falling back to default task list due to API error")
            return TaskList(
                goal=goal,
                target_platforms=target_platforms,
                brand_style=brand_style,
                captions=CaptionTaskConfig(n=3, style="engaging"),
            )


def get_gemini_service() -> GeminiService:
    """Get Gemini service (mock or real based on settings)."""
    if settings.USE_MOCK_GEMINI:
        return MockGeminiService()
    return RealGeminiService()
