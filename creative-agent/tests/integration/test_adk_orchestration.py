"""Integration tests for ADK orchestration and consume endpoint."""

import pytest
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

from app.routers.consume import (
    should_use_adk,
    _extract_url_from_text,
    _generate_assets_with_adk,
)
from promote_autonomy_shared.schemas import TaskList, CaptionTaskConfig, Platform


class TestShouldUseAdk:
    """Test rollout logic for ADK orchestration."""

    def test_returns_false_when_disabled(self, mocker):
        """Test that ADK is not used when disabled."""
        mock_settings = MagicMock()
        mock_settings.USE_ADK_ORCHESTRATION = False
        mock_settings.ADK_ROLLOUT_PERCENTAGE = 100
        mocker.patch("app.routers.consume.settings", mock_settings)

        assert should_use_adk("test_event_id") is False

    def test_returns_false_at_zero_percentage(self, mocker):
        """Test that no events use ADK at 0% rollout."""
        mock_settings = MagicMock()
        mock_settings.USE_ADK_ORCHESTRATION = True
        mock_settings.ADK_ROLLOUT_PERCENTAGE = 0
        mocker.patch("app.routers.consume.settings", mock_settings)

        # Try multiple event IDs
        for i in range(100):
            assert should_use_adk(f"event_{i}") is False

    def test_returns_true_at_100_percentage(self, mocker):
        """Test that all events use ADK at 100% rollout."""
        mock_settings = MagicMock()
        mock_settings.USE_ADK_ORCHESTRATION = True
        mock_settings.ADK_ROLLOUT_PERCENTAGE = 100
        mocker.patch("app.routers.consume.settings", mock_settings)

        # Try multiple event IDs
        for i in range(100):
            assert should_use_adk(f"event_{i}") is True

    def test_deterministic_selection(self, mocker):
        """Test that same event_id always returns same result."""
        mock_settings = MagicMock()
        mock_settings.USE_ADK_ORCHESTRATION = True
        mock_settings.ADK_ROLLOUT_PERCENTAGE = 50
        mocker.patch("app.routers.consume.settings", mock_settings)

        event_id = "test_event_123"
        result1 = should_use_adk(event_id)
        result2 = should_use_adk(event_id)
        result3 = should_use_adk(event_id)

        # Same event_id should always return same result
        assert result1 == result2 == result3

    def test_approximately_50_percent_rollout(self, mocker):
        """Test that ~50% of events use ADK at 50% rollout."""
        mock_settings = MagicMock()
        mock_settings.USE_ADK_ORCHESTRATION = True
        mock_settings.ADK_ROLLOUT_PERCENTAGE = 50
        mocker.patch("app.routers.consume.settings", mock_settings)

        # Test with 1000 different event IDs
        adk_count = sum(1 for i in range(1000) if should_use_adk(f"event_{i}"))

        # Should be roughly 50% (allow 40-60% range for randomness)
        assert 400 <= adk_count <= 600


class TestExtractUrlFromText:
    """Test URL extraction from ADK responses."""

    def test_extracts_url_with_colon_format(self):
        """Test extraction with key: value format."""
        text = 'captions_url: https://storage.googleapis.com/test-bucket/file.json'
        result = _extract_url_from_text(text, "captions")
        assert result == "https://storage.googleapis.com/test-bucket/file.json"

    def test_extracts_url_with_json_format(self):
        """Test extraction with JSON format."""
        text = '"captions_url": "https://storage.googleapis.com/test-bucket/file.json"'
        result = _extract_url_from_text(text, "captions")
        assert result == "https://storage.googleapis.com/test-bucket/file.json"

    def test_extracts_url_with_single_quotes(self):
        """Test extraction with single quotes."""
        text = "'image_url': 'https://storage.googleapis.com/test-bucket/image.png'"
        result = _extract_url_from_text(text, "image")
        assert result == "https://storage.googleapis.com/test-bucket/image.png"

    def test_returns_none_for_missing_url(self):
        """Test that None is returned when URL not found."""
        text = "Some random text without URLs"
        result = _extract_url_from_text(text, "captions")
        assert result is None

    def test_returns_none_for_non_storage_url(self):
        """Test that only GCS URLs are extracted."""
        text = 'captions_url: https://example.com/file.json'
        result = _extract_url_from_text(text, "captions")
        # Non-GCS URLs should be rejected by _validate_gcs_url
        assert result is None

    def test_handles_multiple_urls_returns_first(self):
        """Test extraction when multiple URLs present."""
        text = '''
        captions_url: https://storage.googleapis.com/test-bucket/first.json
        captions_url: https://storage.googleapis.com/test-bucket/second.json
        '''
        result = _extract_url_from_text(text, "captions")
        assert result == "https://storage.googleapis.com/test-bucket/first.json"


@pytest.mark.skip(
    reason="TODO: Mock mismatch - tests mock coordinator.run() but code uses Runner.run() event iterator. "
           "These tests need refactoring to either: "
           "(A) Mock Runner class with proper ADK event objects, OR "
           "(B) Extract parsing logic to _parse_adk_response() for pure unit testing (recommended). "
           "See PR #14 discussion for detailed analysis of options. "
           "Tracked in follow-up issue for post-merge implementation."
)
class TestGenerateAssetsWithAdkParsing:
    """Test result parsing in _generate_assets_with_adk."""

    @pytest.mark.asyncio
    async def test_parses_clean_json_response(self, mocker):
        """Test parsing when ADK returns clean JSON."""
        # Mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.run.return_value = '''
        {
            "captions_url": "https://storage.googleapis.com/test-bucket/captions.json",
            "image_url": "https://storage.googleapis.com/test-bucket/image.png"
        }
        '''
        # Patch where the function is imported in consume.py
        mocker.patch("app.agents.coordinator.get_creative_coordinator", return_value=mock_coordinator)

        # Mock asyncio.to_thread to return the result directly
        async def mock_to_thread(func, *args):
            return func(*args)
        mocker.patch("asyncio.to_thread", side_effect=mock_to_thread)

        # Create task list
        task_list = TaskList(
            goal="Test campaign",
            target_platforms=[Platform.TWITTER],
            captions=CaptionTaskConfig(n=3, style="engaging"),
        )

        # Mock firestore and storage services
        mock_firestore = AsyncMock()
        mock_storage = AsyncMock()

        result = await _generate_assets_with_adk("test_event", task_list, mock_firestore, mock_storage)

        assert "captions_url" in result
        assert result["captions_url"] == "https://storage.googleapis.com/test-bucket/captions.json"
        assert "image_url" in result
        assert result["image_url"] == "https://storage.googleapis.com/test-bucket/image.png"

    @pytest.mark.asyncio
    async def test_parses_multiline_json_response(self, mocker):
        """Test parsing when JSON spans multiple lines."""
        mock_coordinator = MagicMock()
        mock_coordinator.run.return_value = '''
        Here are the generated assets:
        {
            "captions_url": "https://storage.googleapis.com/test-bucket/captions.json",
            "image_url": "https://storage.googleapis.com/test-bucket/image.png",
            "video_url": "https://storage.googleapis.com/test-bucket/video.mp4"
        }
        All assets generated successfully!
        '''
        mocker.patch("app.agents.coordinator.get_creative_coordinator", return_value=mock_coordinator)

        async def mock_to_thread(func, *args):
            return func(*args)
        mocker.patch("asyncio.to_thread", side_effect=mock_to_thread)

        task_list = TaskList(
            goal="Test campaign",
            target_platforms=[Platform.INSTAGRAM_FEED],
            captions=CaptionTaskConfig(n=3, style="engaging"),
        )
        mock_firestore = AsyncMock()
        mock_storage = AsyncMock()

        result = await _generate_assets_with_adk("test_event", task_list, mock_firestore, mock_storage)

        assert len(result) == 3
        assert "captions_url" in result
        assert "image_url" in result
        assert "video_url" in result

    @pytest.mark.asyncio
    async def test_parses_markdown_code_block(self, mocker):
        """Test parsing when JSON is in markdown code block."""
        mock_coordinator = MagicMock()
        mock_coordinator.run.return_value = '''
        Here are the results:

        ```json
        {
            "captions_url": "https://storage.googleapis.com/test-bucket/captions.json"
        }
        ```
        '''
        mocker.patch("app.agents.coordinator.get_creative_coordinator", return_value=mock_coordinator)

        async def mock_to_thread(func, *args):
            return func(*args)
        mocker.patch("asyncio.to_thread", side_effect=mock_to_thread)

        task_list = TaskList(
            goal="Test campaign",
            target_platforms=[Platform.FACEBOOK],
            captions=CaptionTaskConfig(n=3, style="professional"),
        )
        mock_firestore = AsyncMock()
        mock_storage = AsyncMock()

        result = await _generate_assets_with_adk("test_event", task_list, mock_firestore, mock_storage)

        assert "captions_url" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_regex_on_invalid_json(self, mocker):
        """Test regex fallback when JSON parsing fails."""
        mock_coordinator = MagicMock()
        mock_coordinator.run.return_value = '''
        Generated assets successfully!
        captions_url: https://storage.googleapis.com/test-bucket/captions.json
        image_url: https://storage.googleapis.com/test-bucket/image.png
        '''
        mocker.patch("app.agents.coordinator.get_creative_coordinator", return_value=mock_coordinator)

        async def mock_to_thread(func, *args):
            return func(*args)
        mocker.patch("asyncio.to_thread", side_effect=mock_to_thread)

        task_list = TaskList(
            goal="Test campaign",
            target_platforms=[Platform.LINKEDIN],
            captions=CaptionTaskConfig(n=5, style="professional"),
        )
        mock_firestore = AsyncMock()
        mock_storage = AsyncMock()

        result = await _generate_assets_with_adk("test_event", task_list, mock_firestore, mock_storage)

        # Should fall back to regex extraction
        assert "captions_url" in result
        assert result["captions_url"] == "https://storage.googleapis.com/test-bucket/captions.json"

    @pytest.mark.asyncio
    async def test_validates_storage_urls_only(self, mocker):
        """Test that only GCS URLs are accepted."""
        mock_coordinator = MagicMock()
        mock_coordinator.run.return_value = '''
        {
            "captions_url": "https://evil.com/malicious.json",
            "image_url": "https://storage.googleapis.com/test-bucket/image.png"
        }
        '''
        mocker.patch("app.agents.coordinator.get_creative_coordinator", return_value=mock_coordinator)

        async def mock_to_thread(func, *args):
            return func(*args)
        mocker.patch("asyncio.to_thread", side_effect=mock_to_thread)

        task_list = TaskList(
            goal="Test campaign",
            target_platforms=[Platform.YOUTUBE],
            captions=CaptionTaskConfig(n=3, style="engaging"),
        )
        mock_firestore = AsyncMock()
        mock_storage = AsyncMock()

        result = await _generate_assets_with_adk("test_event", task_list, mock_firestore, mock_storage)

        # Only GCS URL should be extracted
        assert "captions_url" not in result  # evil.com rejected
        assert "image_url" in result  # GCS URL accepted
        assert result["image_url"] == "https://storage.googleapis.com/test-bucket/image.png"
