"""ADK Multi-Agent Coordinator for creative asset generation."""

import logging
from google.adk.agents import LlmAgent
from promote_autonomy_shared.schemas import TaskList

from app.agents.tools import (
    generate_captions_tool,
    generate_image_tool,
    generate_video_tool,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_copy_agent() -> LlmAgent:
    """Create ADK agent for caption generation.

    Returns:
        LlmAgent configured for copy writing with Gemini
    """
    return LlmAgent(
        name="copy_writer",
        model="gemini-2.5-flash",
        instruction="""You are a creative copywriter specialized in social media captions.

Your responsibilities:
- Generate engaging, on-brand captions that match the requested style
- Ensure captions are concise and platform-appropriate
- Use the generate_captions_tool to create captions
- Return the result with the captions_url

Always call the generate_captions_tool to generate captions.""",
        description="Generates social media captions using Gemini",
        tools=[generate_captions_tool],
    )


def create_image_agent() -> LlmAgent:
    """Create ADK agent for image generation.

    Returns:
        LlmAgent configured for image creation with Imagen
    """
    return LlmAgent(
        name="image_creator",
        model="gemini-2.5-flash",
        instruction="""You are a visual designer specialized in promotional graphics.

Your responsibilities:
- Generate images that match the requested prompt, size, and aspect ratio
- Ensure images are high quality and platform-appropriate
- Use the generate_image_tool to create images
- Return the result with the image_url

Always call the generate_image_tool to generate images.""",
        description="Generates promotional images using Imagen",
        tools=[generate_image_tool],
    )


def create_video_agent() -> LlmAgent:
    """Create ADK agent for video generation.

    Returns:
        LlmAgent configured for video production with Veo
    """
    return LlmAgent(
        name="video_producer",
        model="gemini-2.5-flash",
        instruction="""You are a video producer specialized in short-form promotional videos.

Your responsibilities:
- Generate videos that match the requested prompt, duration, and aspect ratio
- Ensure videos are high quality and platform-appropriate
- Use the generate_video_tool to create videos
- Return the result with the video_url and any warnings

Always call the generate_video_tool to generate videos.""",
        description="Generates promotional videos using Veo",
        tools=[generate_video_tool],
    )


def create_creative_coordinator() -> LlmAgent:
    """Create ADK coordinator agent that orchestrates all creative agents.

    The coordinator delegates tasks to specialized sub-agents:
    - copy_writer: Generates captions
    - image_creator: Generates images
    - video_producer: Generates videos

    Returns:
        LlmAgent configured to coordinate creative asset generation
    """
    copy_agent = create_copy_agent()
    image_agent = create_image_agent()
    video_agent = create_video_agent()

    coordinator = LlmAgent(
        name="creative_director",
        model="gemini-2.5-flash",
        instruction="""You are a creative director coordinating asset generation for marketing campaigns.

Your job is to delegate tasks to specialized agents based on the task list provided:
- Delegate caption generation to copy_writer agent
- Delegate image generation to image_creator agent
- Delegate video generation to video_producer agent

Important instructions:
1. Delegate ALL tasks in parallel for efficiency (not sequentially)
2. Each agent is independent and can work simultaneously
3. Collect all results and return them in a structured format
4. If any agent fails or returns an error, continue with others and report the error
5. Return results in JSON format with keys: captions_url, image_url, video_url

Example output format:
{
  "captions_url": "https://storage.googleapis.com/...",
  "image_url": "https://storage.googleapis.com/...",
  "video_url": "https://storage.googleapis.com/...",
  "warnings": ["warning message if any"]
}""",
        description="Coordinates creative asset generation across multiple specialized agents",
        sub_agents=[copy_agent, image_agent, video_agent],
    )

    return coordinator


# Singleton instance management
# NOTE: ADK agents are stateless - they don't store request-specific data.
# The singleton pattern is safe because:
# 1. LlmAgent instances only contain configuration (model, instructions, tools)
# 2. Each run() call is independent with its own context
# 3. No mutable state is shared between requests
# 4. Thread-safety: ADK handles concurrent requests internally
_creative_coordinator: LlmAgent | None = None


def get_creative_coordinator() -> LlmAgent:
    """Get or create the creative coordinator agent (singleton).

    The coordinator is safe to share across requests because:
    - ADK agents are stateless (no request-specific data stored)
    - Each run() invocation is independent
    - Configuration (model, tools, instructions) is immutable

    Returns:
        LlmAgent coordinator instance
    """
    global _creative_coordinator

    if _creative_coordinator is None:
        _creative_coordinator = create_creative_coordinator()
        logger.info("[ADK] Created creative coordinator agent with 3 sub-agents")

    return _creative_coordinator
