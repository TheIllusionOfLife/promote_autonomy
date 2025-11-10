"""Unit tests for Creative Agent services."""

import pytest
import json

from promote_autonomy_shared.schemas import (
    CaptionTaskConfig,
    ImageTaskConfig,
    VideoTaskConfig,
    Job,
    JobStatus,
    TaskList,
)

from app.services.copy import MockCopyService
from app.services.image import MockImageService
from app.services.video import MockVideoService
from app.services.firestore import MockFirestoreService
from app.services.storage import MockStorageService


class TestMockCopyService:
    """Tests for MockCopyService."""

    @pytest.mark.asyncio
    async def test_generate_captions_professional(self):
        """Test professional caption generation."""
        service = MockCopyService()
        config = CaptionTaskConfig(n=3, style="professional")

        captions = await service.generate_captions(config, "Launch new product")

        assert len(captions) == 3
        assert all("professional" in c.lower() for c in captions)

    @pytest.mark.asyncio
    async def test_generate_captions_casual(self):
        """Test casual caption generation."""
        service = MockCopyService()
        config = CaptionTaskConfig(n=2, style="casual")

        captions = await service.generate_captions(config, "Summer sale event")

        assert len(captions) == 2
        assert all("casual" in c.lower() for c in captions)

    @pytest.mark.asyncio
    async def test_generate_captions_count(self):
        """Test correct number of captions generated."""
        service = MockCopyService()
        config = CaptionTaskConfig(n=5, style="humorous")

        captions = await service.generate_captions(config, "Test goal")

        assert len(captions) == 5


class TestMockImageService:
    """Tests for MockImageService."""

    @pytest.mark.asyncio
    async def test_generate_image_returns_bytes(self):
        """Test image generation returns PNG bytes."""
        service = MockImageService()
        config = ImageTaskConfig(prompt="Test image prompt", size="1024x1024")

        image_bytes = await service.generate_image(config)

        assert isinstance(image_bytes, bytes)
        assert len(image_bytes) > 0
        # PNG magic number
        assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_generate_image_respects_size(self):
        """Test image generation respects requested size."""
        from PIL import Image
        from io import BytesIO

        service = MockImageService()
        config = ImageTaskConfig(prompt="Test prompt", size="512x512")

        image_bytes = await service.generate_image(config)

        # Verify dimensions
        img = Image.open(BytesIO(image_bytes))
        assert img.size == (512, 512)

    @pytest.mark.asyncio
    async def test_generate_image_different_sizes(self):
        """Test various image sizes."""
        from PIL import Image
        from io import BytesIO

        service = MockImageService()
        sizes = ["256x256", "512x512", "1024x1024", "1920x1080"]

        for size in sizes:
            config = ImageTaskConfig(prompt="Test", size=size)
            image_bytes = await service.generate_image(config)

            img = Image.open(BytesIO(image_bytes))
            expected_width, expected_height = map(int, size.split("x"))
            assert img.size == (expected_width, expected_height)

    @pytest.mark.asyncio
    async def test_generate_image_with_aspect_ratio(self):
        """Test image generation with explicit aspect ratio specification."""
        from PIL import Image
        from io import BytesIO

        service = MockImageService()

        # Test different aspect ratios
        test_cases = [
            ("1024x1024", "1:1", (1024, 1024)),
            ("1080x1920", "9:16", (1080, 1920)),
            ("1920x1080", "16:9", (1920, 1080)),
        ]

        for size, aspect_ratio, expected_dims in test_cases:
            config = ImageTaskConfig(
                prompt="Test",
                size=size,
                aspect_ratio=aspect_ratio,
            )
            image_bytes = await service.generate_image(config)

            img = Image.open(BytesIO(image_bytes))
            assert img.size == expected_dims

    @pytest.mark.asyncio
    async def test_generate_image_respects_max_file_size(self):
        """Test image compression when max_file_size_mb is specified."""
        service = MockImageService()

        # Generate image with max file size constraint
        config = ImageTaskConfig(
            prompt="High quality test image",
            size="1920x1080",
            max_file_size_mb=1.0,  # 1 MB limit
        )
        image_bytes = await service.generate_image(config)

        # Verify size constraint is respected (within reasonable margin)
        size_mb = len(image_bytes) / (1024 * 1024)
        assert size_mb <= 1.1  # Allow 10% margin for compression variation


class TestMockVideoService:
    """Tests for MockVideoService."""

    @pytest.mark.asyncio
    async def test_generate_video_returns_bytes(self):
        """Test video generation returns video bytes (MP4)."""
        service = MockVideoService()
        config = VideoTaskConfig(prompt="Product showcase", duration_sec=30)

        video_bytes = await service.generate_video(config)

        assert isinstance(video_bytes, bytes)
        assert len(video_bytes) > 0
        # Check for MP4 file signature
        assert b"ftyp" in video_bytes[:32]

    @pytest.mark.asyncio
    async def test_generate_video_different_durations(self):
        """Test videos can be generated with different durations."""
        service = MockVideoService()
        durations = [5, 15, 30, 60]

        for duration in durations:
            config = VideoTaskConfig(prompt="Test video", duration_sec=duration)
            video_bytes = await service.generate_video(config)

            assert isinstance(video_bytes, bytes)
            assert len(video_bytes) > 0

    @pytest.mark.asyncio
    async def test_generate_video_with_aspect_ratio(self):
        """Test video generation with explicit aspect ratio specification."""
        service = MockVideoService()

        # Test different aspect ratios
        aspect_ratios = ["16:9", "9:16", "1:1"]

        for aspect_ratio in aspect_ratios:
            config = VideoTaskConfig(
                prompt="Test video",
                duration_sec=10,
                aspect_ratio=aspect_ratio,
            )
            video_bytes = await service.generate_video(config)

            assert isinstance(video_bytes, bytes)
            assert len(video_bytes) > 0
            assert b"ftyp" in video_bytes[:32]

    @pytest.mark.asyncio
    async def test_generate_video_respects_max_file_size(self):
        """Test video compression when max_file_size_mb is specified."""
        service = MockVideoService()

        # Generate video with max file size constraint
        config = VideoTaskConfig(
            prompt="Test video with size limit",
            duration_sec=15,
            max_file_size_mb=10.0,  # 10 MB limit
        )
        video_bytes = await service.generate_video(config)

        # Verify size constraint is respected (mock service creates small files anyway)
        size_mb = len(video_bytes) / (1024 * 1024)
        assert size_mb <= 10.1  # Allow small margin


class TestMockFirestoreService:
    """Tests for MockFirestoreService."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self):
        """Test getting job that doesn't exist."""
        service = MockFirestoreService()

        job = await service.get_job("nonexistent-id")

        assert job is None

    @pytest.mark.asyncio
    async def test_get_existing_job(self):
        """Test getting job that exists."""
        service = MockFirestoreService()

        # Manually add a job
        task_list = TaskList(
            goal="Test goal",
            target_platforms=["twitter"],
            captions=CaptionTaskConfig(n=1),
        )
        service.jobs["test-event-id"] = {
            "event_id": "test-event-id",
            "uid": "test-user",
            "status": JobStatus.PROCESSING,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
        }

        job = await service.get_job("test-event-id")

        assert job is not None
        assert job.event_id == "test-event-id"
        assert job.status == JobStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_update_job_status(self):
        """Test updating job status."""
        service = MockFirestoreService()

        # Create initial job
        task_list = TaskList(
            goal="Test goal",
            target_platforms=["twitter"],
            captions=CaptionTaskConfig(n=1),
        )
        service.jobs["test-event-id"] = {
            "event_id": "test-event-id",
            "uid": "test-user",
            "status": JobStatus.PROCESSING,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
        }

        # Update status
        updated_job = await service.update_job_status(
            "test-event-id",
            JobStatus.COMPLETED,
            captions_url="https://example.com/captions.json",
        )

        assert updated_job.status == JobStatus.COMPLETED
        assert len(updated_job.captions) == 1
        assert updated_job.captions[0] == "https://example.com/captions.json"

    @pytest.mark.asyncio
    async def test_update_nonexistent_job_raises_error(self):
        """Test updating nonexistent job raises error."""
        service = MockFirestoreService()

        with pytest.raises(ValueError, match="not found"):
            await service.update_job_status("nonexistent-id", JobStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_add_job_warning(self):
        """Test adding warning to existing job."""
        service = MockFirestoreService()

        # Create initial job
        task_list = TaskList(
            goal="Test goal",
            target_platforms=["twitter"],
            captions=CaptionTaskConfig(n=1),
        )
        service.jobs["test-event-id"] = {
            "event_id": "test-event-id",
            "uid": "test-user",
            "status": JobStatus.PROCESSING,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
            "warnings": [],
        }

        # Add warning
        updated_job = await service.add_job_warning(
            "test-event-id",
            "Video file size (5.2 MB) exceeds platform limit (4.0 MB)"
        )

        assert len(updated_job.warnings) == 1
        assert "5.2 MB" in updated_job.warnings[0]
        assert "4.0 MB" in updated_job.warnings[0]

    @pytest.mark.asyncio
    async def test_add_multiple_warnings(self):
        """Test adding multiple warnings to same job."""
        service = MockFirestoreService()

        # Create initial job
        task_list = TaskList(
            goal="Test goal",
            target_platforms=["instagram_story", "twitter"],
            captions=CaptionTaskConfig(n=1),
        )
        service.jobs["test-event-id"] = {
            "event_id": "test-event-id",
            "uid": "test-user",
            "status": JobStatus.PROCESSING,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
            "warnings": [],
        }

        # Add first warning
        await service.add_job_warning(
            "test-event-id",
            "Video file size exceeds limit"
        )

        # Add second warning
        updated_job = await service.add_job_warning(
            "test-event-id",
            "Image quality reduced due to size constraints"
        )

        assert len(updated_job.warnings) == 2
        assert "Video file size" in updated_job.warnings[0]
        assert "Image quality" in updated_job.warnings[1]

    @pytest.mark.asyncio
    async def test_add_warning_to_nonexistent_job_raises_error(self):
        """Test adding warning to nonexistent job raises error."""
        service = MockFirestoreService()

        with pytest.raises(ValueError, match="not found"):
            await service.add_job_warning("nonexistent-id", "Some warning")


class TestMockStorageService:
    """Tests for MockStorageService."""

    @pytest.mark.asyncio
    async def test_upload_file(self):
        """Test file upload."""
        service = MockStorageService()

        content = b"test file content"
        url = await service.upload_file(
            event_id="test-event",
            filename="test.txt",
            content=content,
            content_type="text/plain",
        )

        assert isinstance(url, str)
        assert "test-event" in url
        assert "test.txt" in url

    @pytest.mark.asyncio
    async def test_upload_stores_content(self):
        """Test uploaded content is stored."""
        service = MockStorageService()

        content = b"important data"
        await service.upload_file(
            event_id="event-123",
            filename="data.bin",
            content=content,
            content_type="application/octet-stream",
        )

        # Verify stored
        key = "event-123/data.bin"
        assert key in service.files
        assert service.files[key] == content

    @pytest.mark.asyncio
    async def test_upload_multiple_files(self):
        """Test uploading multiple files for same event."""
        service = MockStorageService()

        file1 = b"file one"
        file2 = b"file two"

        url1 = await service.upload_file("event-1", "file1.txt", file1, "text/plain")
        url2 = await service.upload_file("event-1", "file2.txt", file2, "text/plain")

        assert url1 != url2
        assert len(service.files) == 2

    @pytest.mark.asyncio
    async def test_delete_reference_image(self):
        """Test deleting reference image."""
        service = MockStorageService()

        # Upload reference images with different extensions
        service.files["event-123/reference_image.jpg"] = b"jpg data"
        service.files["event-123/reference_image.png"] = b"png data"
        service.files["event-123/other_file.txt"] = b"should not be deleted"

        await service.delete_reference_image("event-123")

        # Verify reference images deleted
        assert "event-123/reference_image.jpg" not in service.files
        assert "event-123/reference_image.png" not in service.files

        # Verify other files not deleted
        assert "event-123/other_file.txt" in service.files

    @pytest.mark.asyncio
    async def test_delete_reference_image_not_exists(self):
        """Test deleting reference image that doesn't exist."""
        service = MockStorageService()

        # Should not raise exception
        await service.delete_reference_image("nonexistent-event")
