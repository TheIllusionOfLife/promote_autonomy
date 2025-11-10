"""Integration tests for ADK coordinator."""

import pytest

# Check if ADK is available
try:
    from google.adk.agents import LlmAgent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

from app.core.config import get_settings
from app.agents.coordinator import (
    create_copy_agent,
    create_image_agent,
    create_video_agent,
    create_creative_coordinator,
    get_creative_coordinator,
)

settings = get_settings()

# Skip all tests if ADK is not installed
pytestmark = pytest.mark.skipif(not ADK_AVAILABLE, reason="google-adk not installed")


def test_create_copy_agent():
    """Test copy agent creation."""
    agent = create_copy_agent()

    assert agent.name == "copy_writer"
    assert agent.model == settings.GEMINI_MODEL
    assert len(agent.tools) == 1
    # Verify tool name
    assert agent.tools[0].__name__ == "generate_captions_tool"


def test_create_image_agent():
    """Test image agent creation."""
    agent = create_image_agent()

    assert agent.name == "image_creator"
    assert agent.model == settings.GEMINI_MODEL
    assert len(agent.tools) == 1
    assert agent.tools[0].__name__ == "generate_image_tool"


def test_create_video_agent():
    """Test video agent creation."""
    agent = create_video_agent()

    assert agent.name == "video_producer"
    assert agent.model == settings.GEMINI_MODEL
    assert len(agent.tools) == 1
    assert agent.tools[0].__name__ == "generate_video_tool"


def test_create_creative_coordinator():
    """Test coordinator creation with sub-agents."""
    coordinator = create_creative_coordinator()

    assert coordinator.name == "creative_director"
    assert coordinator.model == settings.GEMINI_MODEL
    assert len(coordinator.sub_agents) == 3

    # Verify sub-agents
    agent_names = {agent.name for agent in coordinator.sub_agents}
    assert agent_names == {"copy_writer", "image_creator", "video_producer"}


def test_get_creative_coordinator_singleton():
    """Test coordinator singleton pattern with lru_cache."""
    coordinator1 = get_creative_coordinator()
    coordinator2 = get_creative_coordinator()

    # Should return same instance due to @lru_cache
    assert coordinator1 is coordinator2
    assert coordinator1.name == "creative_director"


def test_coordinator_has_correct_instructions():
    """Test coordinator has appropriate instructions for delegation."""
    coordinator = create_creative_coordinator()

    # Check that instruction mentions delegation
    assert "delegate" in coordinator.instruction.lower()
    assert "parallel" in coordinator.instruction.lower()

    # Check for structured output format
    assert "json" in coordinator.instruction.lower()
