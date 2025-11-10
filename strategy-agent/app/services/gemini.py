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


class GeminiService(Protocol):
    """Protocol for Gemini service implementations."""

    async def analyze_reference_image(
        self, image_url: str, goal: str, mime_type: str = "image/jpeg"
    ) -> str:
        """Analyze a reference product image for marketing purposes.

        Args:
            image_url: Public URL to the reference image
            goal: Marketing goal for context
            mime_type: MIME type of image (image/jpeg or image/png)

        Returns:
            Detailed text analysis of the product image
        """
        ...

    async def generate_task_list(
        self,
        goal: str,
        target_platforms: list[Platform],
        brand_style: Optional[BrandStyle] = None,
        reference_analysis: str | None = None
    ) -> TaskList:
        """Generate a task list from a marketing goal.

        Args:
            goal: Marketing goal
            target_platforms: Target social media platforms
            brand_style: Optional brand style guide
            reference_analysis: Optional analysis of reference product image

        Returns:
            Generated task list
        """
        ...


class MockGeminiService:
    """Mock implementation for development without real API."""

    async def analyze_reference_image(
        self, image_url: str, goal: str, mime_type: str = "image/jpeg"
    ) -> str:
        """Generate mock analysis of reference image."""
        logger.info(f"[MOCK] Analyzing reference image: {image_url} for goal: {goal}")

        # Generate mock analysis based on goal keywords
        goal_lower = goal.lower()

        # Detect product type from goal
        product_type = "product"
        if any(word in goal_lower for word in ["shoe", "sneaker", "footwear"]):
            product_type = "shoes"
        elif any(word in goal_lower for word in ["laptop", "computer", "tech"]):
            product_type = "laptop"
        elif any(word in goal_lower for word in ["bottle", "water", "drink"]):
            product_type = "water bottle"
        elif any(word in goal_lower for word in ["coffee", "beans", "beverage"]):
            product_type = "coffee"

        # Generate detailed mock analysis
        analysis = f"""Mock Product Image Analysis for {goal}:

Product Type: {product_type.title()}
Brand Elements: Professional photography with clean composition, modern aesthetic
Colors: Vibrant and eye-catching color palette suitable for social media
Composition: Well-lit product shot with attention to detail
Mood: Contemporary and appealing, conveys quality and desirability
Key Features: High-quality product presentation, suitable for promotional use
Visual Style: Clean, professional product photography with marketing appeal

This analysis is generated in mock mode for development purposes."""

        logger.info(f"[MOCK] Generated analysis: {analysis[:100]}...")
        return analysis

    async def generate_task_list(
        self,
        goal: str,
        target_platforms: list[Platform],
        brand_style: Optional[BrandStyle] = None,
        reference_analysis: str | None = None
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

        # Incorporate reference analysis into prompts if available
        image_prompt_base = f"Modern promotional visual for: {goal[:50]}"
        if reference_analysis:
            # Extract key visual elements from analysis
            analysis_lower = reference_analysis.lower()
            keywords = []
            if "eco" in analysis_lower or "green" in analysis_lower:
                keywords.append("eco-friendly")
            if "nature" in analysis_lower or "outdoor" in analysis_lower:
                keywords.append("nature")
            if "bottle" in analysis_lower:
                keywords.append("bottle")

            if keywords:
                image_prompt_base = f"Product visual incorporating {', '.join(keywords)}: {goal[:40]}"

        task_list = TaskList(
            goal=goal,
            target_platforms=target_platforms,
            brand_style=brand_style,
            captions=CaptionTaskConfig(
                n=5 if has_social else 3,
                style="twitter" if has_social else "engaging",
            ),
            image=ImageTaskConfig(
                prompt=image_prompt_base,
                size=image_size,
                aspect_ratio=image_aspect_ratio,
                max_file_size_mb=min_image_size_mb,
            )
            if has_image or len(goal) > 30 or reference_analysis
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

            settings = get_settings()
            vertexai.init(project=settings.PROJECT_ID, location=settings.LOCATION)
            self.model = GenerativeModel(settings.GEMINI_MODEL)
            self.settings = settings
            logger.info(
                f"Initialized Gemini model: {settings.GEMINI_MODEL} "
                f"in {settings.LOCATION}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    async def analyze_reference_image(
        self, image_url: str, goal: str, mime_type: str = "image/jpeg"
    ) -> str:
        """Analyze reference product image using Gemini vision capabilities.

        Args:
            image_url: Public URL to the reference image
            goal: Marketing goal for context
            mime_type: MIME type of image (image/jpeg or image/png)

        Returns:
            Detailed text analysis of the product image
        """
        from vertexai.generative_models import Part

        prompt = f"""Analyze this product image in detail for marketing purposes. The marketing goal is: {goal}

Please provide a comprehensive analysis including:

1. **Product Type**: What product is shown in the image?
2. **Brand Elements**: Any visible logos, branding, or brand identity elements
3. **Colors**: Dominant colors and color palette
4. **Composition**: How the product is presented (background, lighting, angle)
5. **Mood**: The emotional tone or feeling the image conveys
6. **Key Features**: Notable product features visible in the image
7. **Visual Style**: Photography style, aesthetic, overall visual approach

Provide this analysis in a detailed, structured format (200-400 words) that can inform the creation of marketing captions and visual assets."""

        try:
            # Create image part from URL with correct MIME type
            image_part = Part.from_uri(image_url, mime_type=mime_type)

            # Generate analysis with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.model.generate_content,
                    [image_part, prompt]
                ),
                timeout=self.settings.GEMINI_TIMEOUT_SEC
            )

            analysis = response.text.strip()
            logger.info(f"Generated image analysis: {analysis[:100]}...")
            return analysis

        except Exception as e:
            logger.error(f"Gemini vision API error: {e}")
            # Fallback to basic analysis
            logger.warning("Falling back to basic image analysis")
            return f"Reference product image provided for marketing goal: {goal}. Image available at {image_url}. Please use this as context for creating visually consistent marketing materials."

    async def generate_task_list(
        self,
        goal: str,
        target_platforms: list[Platform],
        brand_style: Optional[BrandStyle] = None,
        reference_analysis: str | None = None
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

        # Build prompt with optional reference analysis
        reference_context = ""
        if reference_analysis:
            reference_context = f"""

Reference Product Image Analysis:
{reference_analysis}

IMPORTANT: Use this product image analysis to inform your captions and visual asset prompts. Ensure generated content is consistent with the product's visual identity, colors, and brand elements described above."""

        prompt = f"""You are a marketing strategist AI. Given a marketing goal and target platforms, generate a structured task list.

Marketing Goal: {goal}
Target Platforms: {platform_names}{reference_context}

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
                timeout=self.settings.GEMINI_TIMEOUT_SEC
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
    settings = get_settings()
    if settings.USE_MOCK_GEMINI:
        return MockGeminiService()
    return RealGeminiService()
