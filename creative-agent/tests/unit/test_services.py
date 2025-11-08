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


class TestMockVideoService:
    """Tests for MockVideoService."""

    @pytest.mark.asyncio
    async def test_generate_video_brief(self):
        """Test video brief generation."""
        service = MockVideoService()
        config = VideoTaskConfig(prompt="Product showcase", duration_sec=30)

        brief = await service.generate_video_brief(config)

        assert isinstance(brief, str)
        assert len(brief) > 0
        assert "30 seconds" in brief or "30" in brief
        assert "Product showcase" in brief

    @pytest.mark.asyncio
    async def test_generate_video_brief_includes_prompt(self):
        """Test brief includes the provided prompt."""
        service = MockVideoService()
        config = VideoTaskConfig(prompt="Unique test prompt 12345", duration_sec=15)

        brief = await service.generate_video_brief(config)

        assert "Unique test prompt 12345" in brief


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
        task_list = TaskList(goal="Test goal")
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
        task_list = TaskList(goal="Test goal")
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
