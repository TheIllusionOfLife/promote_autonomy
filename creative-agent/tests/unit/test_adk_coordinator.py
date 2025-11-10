"""Integration tests for ADK coordinator."""

import pytest
from app.agents.coordinator import (
    create_copy_agent,
    create_image_agent,
    create_video_agent,
    create_creative_coordinator,
    get_creative_coordinator,
)


def test_create_copy_agent():
    """Test copy agent creation."""
    agent = create_copy_agent()

    assert agent.name == "copy_writer"
    assert agent.model == "gemini-2.5-flash"
    assert len(agent.tools) == 1
    # Verify tool name
    assert agent.tools[0].__name__ == "generate_captions_tool"


def test_create_image_agent():
    """Test image agent creation."""
    agent = create_image_agent()

    assert agent.name == "image_creator"
    assert agent.model == "gemini-2.5-flash"
    assert len(agent.tools) == 1
    assert agent.tools[0].__name__ == "generate_image_tool"


def test_create_video_agent():
    """Test video agent creation."""
    agent = create_video_agent()

    assert agent.name == "video_producer"
    assert agent.model == "gemini-2.5-flash"
    assert len(agent.tools) == 1
    assert agent.tools[0].__name__ == "generate_video_tool"


def test_create_creative_coordinator():
    """Test coordinator creation with sub-agents."""
    coordinator = create_creative_coordinator()

    assert coordinator.name == "creative_director"
    assert coordinator.model == "gemini-2.5-flash"
    assert len(coordinator.sub_agents) == 3

    # Verify sub-agents
    agent_names = {agent.name for agent in coordinator.sub_agents}
    assert agent_names == {"copy_writer", "image_creator", "video_producer"}


def test_get_creative_coordinator_singleton():
    """Test coordinator singleton pattern."""
    # Clear singleton first (if any)
    import app.agents.coordinator as coordinator_module
    coordinator_module._creative_coordinator = None

    coordinator1 = get_creative_coordinator()
    coordinator2 = get_creative_coordinator()

    # Should return same instance
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
