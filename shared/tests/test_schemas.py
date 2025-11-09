"""Tests for shared data schemas."""

import pytest
from pydantic import ValidationError

from promote_autonomy_shared.schemas import (
    CaptionTaskConfig,
    ImageTaskConfig,
    Job,
    JobStatus,
    TaskList,
    VideoTaskConfig,
)


class TestCaptionTaskConfig:
    """Tests for CaptionTaskConfig model."""

    def test_valid_caption_config(self):
        """Test valid caption configuration."""
        config = CaptionTaskConfig(n=3, style="twitter")
        assert config.n == 3
        assert config.style == "twitter"

    def test_caption_config_defaults(self):
        """Test default values."""
        config = CaptionTaskConfig(n=5)
        assert config.n == 5
        assert config.style == "engaging"

    def test_caption_config_validation_min(self):
        """Test validation rejects n < 1."""
        with pytest.raises(ValidationError):
            CaptionTaskConfig(n=0)

    def test_caption_config_validation_max(self):
        """Test validation rejects n > 10."""
        with pytest.raises(ValidationError):
            CaptionTaskConfig(n=11)


class TestImageTaskConfig:
    """Tests for ImageTaskConfig model."""

    def test_valid_image_config(self):
        """Test valid image configuration."""
        config = ImageTaskConfig(
            prompt="Modern blue promo visual",
            size="1024x1024",
        )
        assert config.prompt == "Modern blue promo visual"
        assert config.size == "1024x1024"

    def test_image_config_default_size(self):
        """Test default size value."""
        config = ImageTaskConfig(prompt="Test prompt")
        assert config.size == "1024x1024"

    def test_image_config_requires_prompt(self):
        """Test that prompt is required."""
        with pytest.raises(ValidationError):
            ImageTaskConfig()  # type: ignore

    def test_image_config_validates_size_format(self):
        """Test size format validation rejects invalid formats."""
        # Missing 'x' separator
        with pytest.raises(ValidationError, match="Invalid size format"):
            ImageTaskConfig(prompt="Test", size="1024")

        # Non-numeric width
        with pytest.raises(ValidationError, match="Invalid size format"):
            ImageTaskConfig(prompt="Test", size="widthx1024")

        # Non-numeric height
        with pytest.raises(ValidationError, match="Invalid size format"):
            ImageTaskConfig(prompt="Test", size="1024xheight")

        # Empty string
        with pytest.raises(ValidationError, match="Invalid size format"):
            ImageTaskConfig(prompt="Test", size="")

    def test_image_config_validates_positive_dimensions(self):
        """Test size validation rejects zero or negative dimensions."""
        # Zero width
        with pytest.raises(ValidationError, match="Invalid dimensions"):
            ImageTaskConfig(prompt="Test", size="0x1024")

        # Zero height
        with pytest.raises(ValidationError, match="Invalid dimensions"):
            ImageTaskConfig(prompt="Test", size="1024x0")

        # Both zero
        with pytest.raises(ValidationError, match="Invalid dimensions"):
            ImageTaskConfig(prompt="Test", size="0x0")


class TestVideoTaskConfig:
    """Tests for VideoTaskConfig model."""

    def test_valid_video_config(self):
        """Test valid video configuration."""
        config = VideoTaskConfig(
            prompt="Product demo video",
            duration_sec=30,
        )
        assert config.prompt == "Product demo video"
        assert config.duration_sec == 30

    def test_video_config_defaults(self):
        """Test default duration value."""
        config = VideoTaskConfig(prompt="Test prompt")
        assert config.duration_sec == 15

    def test_video_config_validation_min(self):
        """Test validation rejects duration < 5."""
        with pytest.raises(ValidationError):
            VideoTaskConfig(prompt="Test", duration_sec=3)

    def test_video_config_validation_max(self):
        """Test validation rejects duration > 60."""
        with pytest.raises(ValidationError):
            VideoTaskConfig(prompt="Test", duration_sec=61)


class TestTaskList:
    """Tests for TaskList model."""

    def test_valid_task_list_all_tasks(self):
        """Test task list with all task types."""
        task_list = TaskList(
            goal="Launch new feature",
            captions=CaptionTaskConfig(n=3, style="twitter"),
            image=ImageTaskConfig(prompt="Blue visual", size="1024x1024"),
            video=VideoTaskConfig(prompt="Demo video", duration_sec=20),
        )
        assert task_list.goal == "Launch new feature"
        assert task_list.captions is not None
        assert task_list.captions.n == 3
        assert task_list.image is not None
        assert task_list.image.prompt == "Blue visual"
        assert task_list.video is not None
        assert task_list.video.duration_sec == 20

    def test_task_list_only_goal(self):
        """Test task list with only goal (all tasks optional)."""
        task_list = TaskList(goal="Simple goal")
        assert task_list.goal == "Simple goal"
        assert task_list.captions is None
        assert task_list.image is None
        assert task_list.video is None

    def test_task_list_partial_tasks(self):
        """Test task list with some tasks defined."""
        task_list = TaskList(
            goal="Partial tasks",
            captions=CaptionTaskConfig(n=5),
        )
        assert task_list.captions is not None
        assert task_list.image is None
        assert task_list.video is None

    def test_task_list_serialization(self):
        """Test that task list can be serialized to JSON."""
        task_list = TaskList(
            goal="Test",
            captions=CaptionTaskConfig(n=2, style="linkedin"),
        )
        json_data = task_list.model_dump()
        assert json_data["goal"] == "Test"
        assert json_data["captions"]["n"] == 2
        assert json_data["captions"]["style"] == "linkedin"


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_job_status_values(self):
        """Test all job status enum values."""
        assert JobStatus.PENDING_APPROVAL == "pending_approval"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.REJECTED == "rejected"
        assert JobStatus.FAILED == "failed"

    def test_job_status_from_string(self):
        """Test creating JobStatus from string."""
        status = JobStatus("pending_approval")
        assert status == JobStatus.PENDING_APPROVAL


class TestJob:
    """Tests for Job model."""

    def test_valid_job_minimal(self):
        """Test job with minimal required fields."""
        task_list = TaskList(
            goal="Test goal",
            captions=CaptionTaskConfig(n=1),
        )
        job = Job(
            event_id="01JD4S3ABC",
            uid="user123",
            status=JobStatus.PENDING_APPROVAL,
            task_list=task_list,
            created_at="2025-11-08T10:00:00Z",
            updated_at="2025-11-08T10:00:00Z",
        )
        assert job.event_id == "01JD4S3ABC"
        assert job.uid == "user123"
        assert job.status == JobStatus.PENDING_APPROVAL
        assert job.task_list.goal == "Test goal"
        assert job.captions == []
        assert job.images == []
        assert job.videos == []
        assert job.audit_logs == []
        assert job.approved_at is None

    def test_job_with_approval(self):
        """Test job with approval timestamp."""
        task_list = TaskList(goal="Test")
        job = Job(
            event_id="01JD4S3ABC",
            uid="user123",
            status=JobStatus.PROCESSING,
            task_list=task_list,
            created_at="2025-11-08T10:00:00Z",
            updated_at="2025-11-08T10:05:00Z",
            approved_at="2025-11-08T10:05:00Z",
        )
        assert job.approved_at == "2025-11-08T10:05:00Z"
        assert job.status == JobStatus.PROCESSING

    def test_job_with_generated_assets(self):
        """Test job with generated assets."""
        task_list = TaskList(goal="Test")
        job = Job(
            event_id="01JD4S3ABC",
            uid="user123",
            status=JobStatus.COMPLETED,
            task_list=task_list,
            created_at="2025-11-08T10:00:00Z",
            updated_at="2025-11-08T10:10:00Z",
            captions=["Caption 1", "Caption 2"],
            images=["gs://bucket/image1.png"],
            videos=["gs://bucket/video1.mp4"],
        )
        assert len(job.captions) == 2
        assert len(job.images) == 1
        assert len(job.videos) == 1

    def test_job_serialization_deserialization(self):
        """Test job can be serialized and deserialized."""
        task_list = TaskList(
            goal="Round trip test",
            captions=CaptionTaskConfig(n=3),
        )
        original_job = Job(
            event_id="01JD4S3ABC",
            uid="user123",
            status=JobStatus.PENDING_APPROVAL,
            task_list=task_list,
            created_at="2025-11-08T10:00:00Z",
            updated_at="2025-11-08T10:00:00Z",
        )

        # Serialize
        json_data = original_job.model_dump()

        # Deserialize
        reconstructed_job = Job(**json_data)

        assert reconstructed_job.event_id == original_job.event_id
        assert reconstructed_job.uid == original_job.uid
        assert reconstructed_job.status == original_job.status
        assert reconstructed_job.task_list.goal == original_job.task_list.goal

    def test_job_status_transitions(self):
        """Test valid status transitions."""
        task_list = TaskList(goal="Status test")

        # pending_approval
        job = Job(
            event_id="01JD4S3ABC",
            uid="user123",
            status=JobStatus.PENDING_APPROVAL,
            task_list=task_list,
            created_at="2025-11-08T10:00:00Z",
            updated_at="2025-11-08T10:00:00Z",
        )
        assert job.status == JobStatus.PENDING_APPROVAL

        # Can transition to processing
        job.status = JobStatus.PROCESSING
        assert job.status == JobStatus.PROCESSING

        # Can transition to completed
        job.status = JobStatus.COMPLETED
        assert job.status == JobStatus.COMPLETED

        # Can transition to failed
        job2 = Job(
            event_id="01JD4S3XYZ",
            uid="user123",
            status=JobStatus.PROCESSING,
            task_list=task_list,
            created_at="2025-11-08T10:00:00Z",
            updated_at="2025-11-08T10:00:00Z",
        )
        job2.status = JobStatus.FAILED
        assert job2.status == JobStatus.FAILED
