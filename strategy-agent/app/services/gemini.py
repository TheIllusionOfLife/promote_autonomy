"""Gemini API service for task list generation."""

import asyncio
import json
import logging
import re
from typing import Protocol

from promote_autonomy_shared.schemas import (
    CaptionTaskConfig,
    ImageTaskConfig,
    TaskList,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiService(Protocol):
    """Protocol for Gemini service implementations."""

    async def generate_task_list(self, goal: str) -> TaskList:
        """Generate a task list from a marketing goal."""
        ...


class MockGeminiService:
    """Mock implementation for development without real API."""

    async def generate_task_list(self, goal: str) -> TaskList:
        """Generate a mock task list based on the goal."""
        logger.info(f"[MOCK] Generating task list for goal: {goal}")

        # Simple heuristic: generate different tasks based on goal keywords
        has_social = any(
            word in goal.lower() for word in ["twitter", "social", "post", "tweet"]
        )
        has_image = any(
            word in goal.lower()
            for word in ["visual", "image", "graphic", "picture", "photo"]
        )

        task_list = TaskList(
            goal=goal,
            captions=CaptionTaskConfig(
                n=5 if has_social else 3,
                style="twitter" if has_social else "engaging",
            ),
            image=ImageTaskConfig(
                prompt=f"Modern promotional visual for: {goal[:50]}",
                size="1024x1024",
            )
            if has_image or len(goal) > 30
            else None,
        )

        logger.info(f"[MOCK] Generated task list: {task_list.model_dump_json()}")
        return task_list


class RealGeminiService:
    """Real Gemini API implementation."""

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

    async def generate_task_list(self, goal: str) -> TaskList:
        """Generate a task list using Gemini API."""
        prompt = f"""You are a marketing strategist AI. Given a marketing goal, generate a structured task list.

Marketing Goal: {goal}

Generate a JSON object with this structure:
{{
  "goal": "<the goal>",
  "captions": {{"n": <1-10>, "style": "<engaging|twitter|linkedin>"}},
  "image": {{"prompt": "<image description>", "size": "1024x1024"}} or null,
  "video": {{"prompt": "<video description>", "duration_sec": <5-60>}} or null
}}

Rules:
- Always include captions (1-10 captions)
- Include image if goal mentions visuals or is substantial
- Include video only if explicitly mentioned or goal is major campaign
- Be specific and actionable in prompts
- Return ONLY valid JSON, no markdown formatting
"""

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            response_text = response.text.strip()

            # Extract JSON from markdown code blocks using regex
            # Handles formats: ```json\n{...}\n```, ```\n{...}\n```, or plain {...}
            json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1).strip()

            # Parse JSON to TaskList
            data = json.loads(response_text)
            task_list = TaskList(**data)

            logger.info(f"Generated task list via Gemini: {task_list.model_dump_json()}")
            return task_list

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Fallback to basic task list
            logger.warning("Falling back to default task list due to API error")
            return TaskList(
                goal=goal,
                captions=CaptionTaskConfig(n=3, style="engaging"),
            )


def get_gemini_service() -> GeminiService:
    """Get Gemini service (mock or real based on settings)."""
    if settings.USE_MOCK_GEMINI:
        return MockGeminiService()
    return RealGeminiService()
