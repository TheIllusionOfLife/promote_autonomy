"""Unit tests for video generation services (VEO integration)."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from promote_autonomy_shared.schemas import VideoTaskConfig


class TestVideoServiceProtocol:
    """Tests for VideoService protocol with bytes return type."""

    @pytest.mark.asyncio
    async def test_mock_video_service_returns_bytes(self):
        """Test MockVideoService returns video bytes (MP4 format)."""
        from app.services.video import MockVideoService

        service = MockVideoService()
        config = VideoTaskConfig(prompt="Test video prompt", duration_sec=15)

        video_bytes = await service.generate_video(config)

        assert isinstance(video_bytes, bytes)
        assert len(video_bytes) > 0

    @pytest.mark.asyncio
    async def test_mock_video_has_mp4_header(self):
        """Test mock video has valid MP4 file header."""
        from app.services.video import MockVideoService

        service = MockVideoService()
        config = VideoTaskConfig(prompt="Product demo", duration_sec=30)

        video_bytes = await service.generate_video(config)

        # MP4 files start with 'ftyp' box (after initial size bytes)
        # Typical pattern: [4 bytes size][4 bytes 'ftyp'][...]
        assert b"ftyp" in video_bytes[:32]


class TestMockVideoService:
    """Tests for MockVideoService generating mock MP4 bytes."""

    @pytest.mark.asyncio
    async def test_generates_valid_mp4_structure(self):
        """Test mock video has basic MP4 structure."""
        from app.services.video import MockVideoService

        service = MockVideoService()
        config = VideoTaskConfig(prompt="Marketing video", duration_sec=20)

        video_bytes = await service.generate_video(config)

        # Check for MP4 file type box
        assert b"ftyp" in video_bytes
        # Check for movie data box
        assert b"mdat" in video_bytes or b"moov" in video_bytes

    @pytest.mark.asyncio
    async def test_different_durations(self):
        """Test mock videos can be generated with different durations."""
        from app.services.video import MockVideoService

        service = MockVideoService()
        durations = [5, 15, 30, 60]

        for duration in durations:
            config = VideoTaskConfig(prompt="Test", duration_sec=duration)
            video_bytes = await service.generate_video(config)

            assert isinstance(video_bytes, bytes)
            assert len(video_bytes) > 0


class TestRealVeoVideoService:
    """Tests for RealVeoVideoService using google.genai SDK."""

    @pytest.mark.asyncio
    async def test_generate_video_success(self):
        """Test successful video generation with VEO API."""
        from app.services.video import RealVeoVideoService

        # Mock google.genai module
        mock_genai = Mock()
        mock_genai_types = Mock()
        mock_config = Mock()
        mock_config.aspect_ratio = "16:9"
        mock_genai_types.GenerateVideosConfig = Mock(return_value=mock_config)

        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.done = False
        mock_operation.error = None  # No error for success case
        mock_result = Mock()
        mock_video = Mock()
        mock_video.uri = "gs://test-bucket/test-video.mp4"
        mock_result.generated_videos = [mock_video]

        # Mock operation polling: first not done, then done
        call_count = [0]

        def get_operation(op):
            call_count[0] += 1
            if call_count[0] >= 2:
                mock_operation.done = True
                mock_operation.error = None  # Ensure no error on completion
                mock_operation.result = mock_result
            return mock_operation

        mock_client.operations.get = get_operation
        mock_client.models.generate_videos = Mock(return_value=mock_operation)
        mock_genai.Client = Mock(return_value=mock_client)
        mock_genai.types = mock_genai_types

        # Mock GCS download and storage
        mock_video_bytes = b"fake mp4 video data with ftyp header"
        mock_storage = Mock()

        with patch.dict("sys.modules", {
            "google.genai": mock_genai,
            "google.genai.types": mock_genai_types,
            "google.cloud.storage": mock_storage
        }):
            with patch("app.services.video.get_settings") as mock_get_settings:
                mock_settings = Mock()
                mock_settings.PROJECT_ID = "test-project"
                mock_settings.LOCATION = "us-central1"
                mock_settings.VEO_MODEL = "veo-3.0-generate-001"
                mock_settings.VIDEO_OUTPUT_GCS_BUCKET = "gs://test-bucket/veo-output"
                mock_settings.VEO_TIMEOUT_SEC = 360
                mock_settings.VEO_POLLING_INTERVAL_SEC = 0.001  # Fast polling for tests
                mock_get_settings.return_value = mock_settings

                service = RealVeoVideoService()
                service._download_from_gcs = AsyncMock(return_value=mock_video_bytes)

                config = VideoTaskConfig(prompt="Test video", duration_sec=15)
                video_bytes = await service.generate_video(config)

                assert video_bytes == mock_video_bytes
                assert mock_client.models.generate_videos.called

    @pytest.mark.asyncio
    async def test_generate_video_timeout(self):
        """Test timeout handling during video generation."""
        from app.services.video import RealVeoVideoService

        # Mock google.genai module
        mock_genai = Mock()
        mock_genai_types = Mock()
        mock_config = Mock()
        mock_genai_types.GenerateVideosConfig = Mock(return_value=mock_config)

        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.done = False  # Always not done

        mock_client.operations.get = Mock(return_value=mock_operation)
        mock_client.models.generate_videos = Mock(return_value=mock_operation)
        mock_genai.Client = Mock(return_value=mock_client)
        mock_genai.types = mock_genai_types

        mock_storage = Mock()

        with patch.dict("sys.modules", {
            "google.genai": mock_genai,
            "google.genai.types": mock_genai_types,
            "google.cloud.storage": mock_storage
        }):
            with patch("app.services.video.get_settings") as mock_get_settings:
                mock_settings = Mock()
                mock_settings.PROJECT_ID = "test-project"
                mock_settings.LOCATION = "us-central1"
                mock_settings.VEO_MODEL = "veo-3.0-generate-001"
                mock_settings.VIDEO_OUTPUT_GCS_BUCKET = "gs://test"
                mock_settings.VEO_TIMEOUT_SEC = 1  # Very short timeout for testing
                mock_settings.VEO_POLLING_INTERVAL_SEC = 0.1
                mock_get_settings.return_value = mock_settings

                service = RealVeoVideoService()
                config = VideoTaskConfig(prompt="Test", duration_sec=15)

                with pytest.raises(TimeoutError, match="Video generation timed out"):
                    await service.generate_video(config)

    @pytest.mark.asyncio
    async def test_generate_video_with_aspect_ratio(self):
        """Test video generation respects aspect ratio configuration."""
        from app.services.video import RealVeoVideoService

        # Mock google.genai module
        mock_genai = Mock()
        mock_genai_types = Mock()
        mock_config = Mock()
        mock_config.aspect_ratio = "16:9"
        mock_genai_types.GenerateVideosConfig = Mock(return_value=mock_config)

        mock_client = Mock()
        mock_operation = Mock()
        mock_operation.done = True
        mock_operation.error = None  # No error for success case
        mock_result = Mock()
        mock_video = Mock()
        mock_video.uri = "gs://test-bucket/video.mp4"
        mock_result.generated_videos = [mock_video]
        mock_operation.result = mock_result

        mock_client.operations.get = Mock(return_value=mock_operation)

        # Capture generate_videos call arguments
        generate_videos_calls = []

        def capture_generate_videos(*args, **kwargs):
            generate_videos_calls.append((args, kwargs))
            return mock_operation

        mock_client.models.generate_videos = capture_generate_videos
        mock_genai.Client = Mock(return_value=mock_client)
        mock_genai.types = mock_genai_types

        mock_storage = Mock()

        with patch.dict("sys.modules", {
            "google.genai": mock_genai,
            "google.genai.types": mock_genai_types,
            "google.cloud.storage": mock_storage
        }):
            with patch("app.services.video.get_settings") as mock_get_settings:
                mock_settings = Mock()
                mock_settings.PROJECT_ID = "test-project"
                mock_settings.LOCATION = "us-central1"
                mock_settings.VEO_MODEL = "veo-3.0-generate-001"
                mock_settings.VIDEO_OUTPUT_GCS_BUCKET = "gs://test-bucket/veo-output"
                mock_settings.VEO_TIMEOUT_SEC = 360
                mock_settings.VEO_POLLING_INTERVAL_SEC = 0.001  # Fast polling for tests
                mock_get_settings.return_value = mock_settings

                service = RealVeoVideoService()
                service._download_from_gcs = AsyncMock(return_value=b"video data")

                config = VideoTaskConfig(prompt="Test", duration_sec=15)
                await service.generate_video(config)

                # Verify aspect_ratio was passed in config
                assert len(generate_videos_calls) == 1
                call_kwargs = generate_videos_calls[0][1]
                assert "config" in call_kwargs
                assert call_kwargs["config"].aspect_ratio == "16:9"


class TestGCSDownload:
    """Tests for GCS download functionality."""

    @pytest.mark.asyncio
    async def test_download_from_gcs_success(self):
        """Test successful download from GCS URI."""
        from app.services.video import RealVeoVideoService

        mock_video_data = b"test video content"

        # Mock google.cloud.storage module and Client
        mock_storage_module = Mock()
        mock_blob = Mock()
        mock_blob.download_as_bytes = Mock(return_value=mock_video_data)

        mock_bucket = Mock()
        mock_bucket.blob = Mock(return_value=mock_blob)

        mock_storage_client = Mock()
        mock_storage_client.bucket = Mock(return_value=mock_bucket)
        mock_storage_module.Client = Mock(return_value=mock_storage_client)

        mock_genai = Mock()

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google.cloud.storage": mock_storage_module}):
            with patch("app.core.config.get_settings") as mock_get_settings:
                mock_settings = Mock()
                mock_settings.PROJECT_ID = "test-project"
                mock_settings.LOCATION = "us-central1"
                mock_get_settings.return_value = mock_settings

                service = RealVeoVideoService()

                video_bytes = await service._download_from_gcs("gs://test-bucket/path/to/video.mp4")

                assert video_bytes == mock_video_data
                mock_storage_client.bucket.assert_called_with("test-bucket")
                mock_bucket.blob.assert_called_with("path/to/video.mp4")

    @pytest.mark.asyncio
    async def test_download_from_gcs_parses_uri(self):
        """Test GCS URI parsing extracts bucket and path correctly."""
        from app.services.video import RealVeoVideoService

        # Mock google.cloud.storage module
        mock_storage_module = Mock()
        mock_blob = Mock()
        mock_blob.download_as_bytes = Mock(return_value=b"data")

        mock_bucket = Mock()
        mock_bucket.blob = Mock(return_value=mock_blob)

        mock_storage_client = Mock()
        mock_storage_client.bucket = Mock(return_value=mock_bucket)
        mock_storage_module.Client = Mock(return_value=mock_storage_client)

        mock_genai = Mock()

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google.cloud.storage": mock_storage_module}):
            with patch("app.core.config.get_settings") as mock_get_settings:
                mock_settings = Mock()
                mock_settings.PROJECT_ID = "test-project"
                mock_settings.LOCATION = "us-central1"
                mock_get_settings.return_value = mock_settings

                service = RealVeoVideoService()

                # Test various URI formats
                test_cases = [
                    ("gs://my-bucket/video.mp4", "my-bucket", "video.mp4"),
                    ("gs://bucket-name/folder/subfolder/file.mp4", "bucket-name", "folder/subfolder/file.mp4"),
                ]

                for uri, expected_bucket, expected_path in test_cases:
                    await service._download_from_gcs(uri)

                    # Verify bucket and blob path extraction
                    assert mock_storage_client.bucket.call_args[0][0] == expected_bucket
                    assert mock_bucket.blob.call_args[0][0] == expected_path


class TestVideoServiceFactory:
    """Tests for video service factory function."""

    def test_get_video_service_returns_mock_when_flag_set(self):
        """Test factory returns MockVideoService when USE_MOCK_VEO is True."""
        from app.services.video import get_video_service

        with patch("app.services.video.get_settings") as mock_settings:
            mock_settings.return_value.USE_MOCK_VEO = True
            mock_settings.return_value.USE_MOCK_GEMINI = False

            service = get_video_service()

            # Should be MockVideoService
            assert service.__class__.__name__ == "MockVideoService"

    def test_get_video_service_returns_real_when_flag_false(self):
        """Test factory returns RealVeoVideoService when USE_MOCK_VEO is False."""
        from app.services.video import get_video_service

        # Reset singleton to None for this test
        import app.services.video
        app.services.video._real_video_service = None
        app.services.video._mock_video_service = None

        mock_genai = Mock()
        mock_storage = Mock()

        with patch.dict("sys.modules", {"google.genai": mock_genai, "google.cloud.storage": mock_storage}):
            with patch("app.services.video.get_settings") as mock_settings:
                mock_settings.return_value.USE_MOCK_VEO = False
                mock_settings.return_value.USE_MOCK_GEMINI = False
                mock_settings.return_value.VEO_MODEL = "veo-3.0-generate-001"
                mock_settings.return_value.VIDEO_OUTPUT_GCS_BUCKET = "gs://test"
                mock_settings.return_value.PROJECT_ID = "test-project"
                mock_settings.return_value.LOCATION = "us-central1"
                mock_settings.return_value.VEO_TIMEOUT_SEC = 360
                mock_settings.return_value.VEO_POLLING_INTERVAL_SEC = 15

                service = get_video_service()

                # Should be RealVeoVideoService
                assert service.__class__.__name__ == "RealVeoVideoService"

    def test_get_video_service_singleton_pattern(self):
        """Test factory returns same instance on repeated calls."""
        from app.services.video import get_video_service

        with patch("app.services.video.get_settings") as mock_settings:
            mock_settings.return_value.USE_MOCK_VEO = True
            mock_settings.return_value.USE_MOCK_GEMINI = False

            service1 = get_video_service()
            service2 = get_video_service()

            assert service1 is service2
