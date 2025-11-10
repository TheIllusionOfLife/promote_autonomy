"""Unit tests for ADK tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

# Check if ADK is available (needed for coordinator to work)
try:
    from google.adk.agents import LlmAgent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

from app.agents.tools import (
    generate_captions_tool,
    generate_image_tool,
    generate_video_tool,
)

# Skip all tests if ADK is not installed (tools tests don't need it but good to be consistent)
# Note: The tools themselves work without ADK, but they're only used with ADK
pytestmark = pytest.mark.skipif(not ADK_AVAILABLE, reason="google-adk not installed")


@pytest.mark.asyncio
async def test_generate_captions_tool(mocker):
    """Test caption generation tool."""
    # Mock services
    mock_copy_service = AsyncMock()
    mock_copy_service.generate_captions.return_value = [
        "Caption 1",
        "Caption 2",
        "Caption 3"
    ]
    mocker.patch("app.agents.tools.get_copy_service", return_value=mock_copy_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/captions.json"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool
    config = {"n": 3, "style": "engaging"}
    result = await generate_captions_tool(config, "Test goal", "test_event_id")

    # Verify
    assert "captions_url" in result
    assert result["captions_url"] == "https://storage.googleapis.com/test/captions.json"
    mock_copy_service.generate_captions.assert_called_once()
    mock_storage_service.upload_file.assert_called_once()


@pytest.mark.asyncio
async def test_generate_captions_tool_error_handling(mocker):
    """Test caption generation tool handles errors gracefully."""
    # Mock service to raise exception
    mock_copy_service = AsyncMock()
    mock_copy_service.generate_captions.side_effect = Exception("Gemini API error")
    mocker.patch("app.agents.tools.get_copy_service", return_value=mock_copy_service)

    mock_storage_service = AsyncMock()
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool
    config = {"n": 3, "style": "engaging"}
    result = await generate_captions_tool(config, "Test goal", "test_event_id")

    # Verify error is returned, not raised
    assert "error" in result
    assert "Caption generation failed" in result["error"]


@pytest.mark.asyncio
async def test_generate_image_tool(mocker):
    """Test image generation tool."""
    # Mock services
    mock_image_service = AsyncMock()
    mock_image_service.generate_image.return_value = b"fake_image_bytes"
    mocker.patch("app.agents.tools.get_image_service", return_value=mock_image_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/image.png"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool
    config = {"prompt": "Test image", "size": "1024x1024"}
    result = await generate_image_tool(config, "test_event_id")

    # Verify
    assert "image_url" in result
    assert result["image_url"] == "https://storage.googleapis.com/test/image.png"
    mock_image_service.generate_image.assert_called_once()
    mock_storage_service.upload_file.assert_called_once_with(
        event_id="test_event_id",
        filename="image.png",
        content=b"fake_image_bytes",
        content_type="image/png"
    )


@pytest.mark.asyncio
async def test_generate_image_tool_with_compression(mocker):
    """Test image generation tool with max_file_size_mb."""
    # Mock services
    mock_image_service = AsyncMock()
    mock_image_service.generate_image.return_value = b"fake_compressed_image"
    mocker.patch("app.agents.tools.get_image_service", return_value=mock_image_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/image.jpg"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool with compression
    config = {"prompt": "Test image", "size": "1024x1024", "max_file_size_mb": 4.0}
    result = await generate_image_tool(config, "test_event_id")

    # Verify JPEG format used
    assert "image_url" in result
    mock_storage_service.upload_file.assert_called_once_with(
        event_id="test_event_id",
        filename="image.jpg",  # JPEG when compressed
        content=b"fake_compressed_image",
        content_type="image/jpeg"
    )


@pytest.mark.asyncio
async def test_generate_video_tool(mocker):
    """Test video generation tool."""
    # Mock services
    mock_video_service = AsyncMock()
    # 2MB video (within limit)
    mock_video_service.generate_video.return_value = b"x" * (2 * 1024 * 1024)
    mocker.patch("app.agents.tools.get_video_service", return_value=mock_video_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/video.mp4"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool
    config = {"prompt": "Test video", "duration_sec": 8}
    result = await generate_video_tool(config, "test_event_id")

    # Verify
    assert "video_url" in result
    assert result["video_url"] == "https://storage.googleapis.com/test/video.mp4"
    assert "warning" not in result  # No warning for small video
    mock_video_service.generate_video.assert_called_once()


@pytest.mark.asyncio
async def test_generate_video_tool_with_size_warning(mocker):
    """Test video generation tool with file size warning."""
    # Mock services - video exceeds size limit
    mock_video_service = AsyncMock()
    # 6MB video (exceeds 4MB limit)
    mock_video_service.generate_video.return_value = b"x" * (6 * 1024 * 1024)
    mocker.patch("app.agents.tools.get_video_service", return_value=mock_video_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/video.mp4"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool with 4MB limit
    config = {"prompt": "Test video", "duration_sec": 8, "max_file_size_mb": 4.0}
    result = await generate_video_tool(config, "test_event_id")

    # Verify warning is included
    assert "video_url" in result
    assert "warning" in result
    assert "6.00 MB" in result["warning"]
    assert "4.0 MB" in result["warning"]


@pytest.mark.asyncio
async def test_generate_video_tool_error_handling(mocker):
    """Test video generation tool handles errors gracefully."""
    # Mock service to raise exception
    mock_video_service = AsyncMock()
    mock_video_service.generate_video.side_effect = Exception("Veo API error")
    mocker.patch("app.agents.tools.get_video_service", return_value=mock_video_service)

    mock_storage_service = AsyncMock()
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool
    config = {"prompt": "Test video", "duration_sec": 8}
    result = await generate_video_tool(config, "test_event_id")

    # Verify error is returned, not raised
    assert "error" in result
    assert "Video generation failed" in result["error"]
