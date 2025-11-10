"""Tests for shared data schemas."""

import pytest
from pydantic import ValidationError

from promote_autonomy_shared.schemas import (
    BrandColor,
    BrandStyle,
    BrandTone,
    CaptionTaskConfig,
    ImageTaskConfig,
    Job,
    JobStatus,
    Platform,
    PlatformSpec,
    PLATFORM_SPECS,
    TaskList,
    VideoTaskConfig,
)


class TestPlatform:
    """Tests for Platform enum."""

    def test_platform_enum_values(self):
        """Test all platform enum values exist."""
        assert Platform.INSTAGRAM_FEED == "instagram_feed"
        assert Platform.INSTAGRAM_STORY == "instagram_story"
        assert Platform.TWITTER == "twitter"
        assert Platform.FACEBOOK == "facebook"
        assert Platform.LINKEDIN == "linkedin"
        assert Platform.YOUTUBE == "youtube"

    def test_platform_from_string(self):
        """Test creating Platform from string."""
        platform = Platform("instagram_feed")
        assert platform == Platform.INSTAGRAM_FEED

    def test_platform_invalid_value(self):
        """Test invalid platform value raises error."""
        with pytest.raises(ValueError):
            Platform("tiktok")


class TestPlatformSpec:
    """Tests for PlatformSpec model."""

    def test_valid_platform_spec(self):
        """Test creating valid platform spec."""
        spec = PlatformSpec(
            platform=Platform.INSTAGRAM_FEED,
            image_size="1080x1080",
            image_aspect_ratio="1:1",
            max_image_size_mb=4.0,
            video_size="1080x1080",
            video_aspect_ratio="1:1",
            max_video_length_sec=60,
            max_video_size_mb=4.0,
            caption_max_length=2200,
        )
        assert spec.platform == Platform.INSTAGRAM_FEED
        assert spec.image_size == "1080x1080"
        assert spec.image_aspect_ratio == "1:1"
        assert spec.max_image_size_mb == 4.0
        assert spec.video_aspect_ratio == "1:1"
        assert spec.max_video_length_sec == 60

    def test_platform_spec_requires_all_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            PlatformSpec(platform=Platform.INSTAGRAM_FEED)  # type: ignore


class TestPlatformSpecs:
    """Tests for PLATFORM_SPECS constant."""

    def test_all_platforms_have_specs(self):
        """Test that all platforms have specifications defined."""
        for platform in Platform:
            assert platform in PLATFORM_SPECS, f"Missing spec for {platform}"

    def test_instagram_feed_spec(self):
        """Test Instagram Feed specifications."""
        spec = PLATFORM_SPECS[Platform.INSTAGRAM_FEED]
        assert spec.platform == Platform.INSTAGRAM_FEED
        assert spec.image_size == "1080x1080"
        assert spec.image_aspect_ratio == "1:1"
        assert spec.max_image_size_mb == 4.0
        assert spec.video_size == "1080x1080"
        assert spec.video_aspect_ratio == "1:1"
        assert spec.max_video_length_sec == 60
        assert spec.max_video_size_mb == 4.0
        assert spec.caption_max_length == 2200

    def test_instagram_story_spec(self):
        """Test Instagram Story specifications."""
        spec = PLATFORM_SPECS[Platform.INSTAGRAM_STORY]
        assert spec.platform == Platform.INSTAGRAM_STORY
        assert spec.image_size == "1080x1920"
        assert spec.image_aspect_ratio == "9:16"
        assert spec.max_image_size_mb == 4.0
        assert spec.video_size == "1080x1920"
        assert spec.video_aspect_ratio == "9:16"
        assert spec.max_video_length_sec == 15
        assert spec.max_video_size_mb == 4.0
        assert spec.caption_max_length == 2200

    def test_twitter_spec(self):
        """Test Twitter specifications."""
        spec = PLATFORM_SPECS[Platform.TWITTER]
        assert spec.platform == Platform.TWITTER
        assert spec.image_size == "1200x675"
        assert spec.image_aspect_ratio == "16:9"
        assert spec.max_image_size_mb == 5.0
        assert spec.video_size == "1280x720"
        assert spec.video_aspect_ratio == "16:9"
        assert spec.max_video_length_sec == 140
        assert spec.max_video_size_mb == 512.0
        assert spec.caption_max_length == 280

    def test_facebook_spec(self):
        """Test Facebook specifications."""
        spec = PLATFORM_SPECS[Platform.FACEBOOK]
        assert spec.platform == Platform.FACEBOOK
        assert spec.image_size == "1200x630"
        assert spec.image_aspect_ratio == "1.91:1"
        assert spec.max_image_size_mb == 8.0
        assert spec.video_size == "1280x720"
        assert spec.video_aspect_ratio == "16:9"
        assert spec.max_video_length_sec == 240
        assert spec.max_video_size_mb == 4096.0
        assert spec.caption_max_length == 63206

    def test_linkedin_spec(self):
        """Test LinkedIn specifications."""
        spec = PLATFORM_SPECS[Platform.LINKEDIN]
        assert spec.platform == Platform.LINKEDIN
        assert spec.image_size == "1200x627"
        assert spec.image_aspect_ratio == "1.91:1"
        assert spec.max_image_size_mb == 5.0
        assert spec.video_size == "1280x720"
        assert spec.video_aspect_ratio == "16:9"
        assert spec.max_video_length_sec == 600
        assert spec.max_video_size_mb == 5120.0
        assert spec.caption_max_length == 3000

    def test_youtube_spec(self):
        """Test YouTube specifications."""
        spec = PLATFORM_SPECS[Platform.YOUTUBE]
        assert spec.platform == Platform.YOUTUBE
        assert spec.image_size == "1280x720"
        assert spec.image_aspect_ratio == "16:9"
        assert spec.max_image_size_mb == 2.0
        assert spec.video_size == "1920x1080"
        assert spec.video_aspect_ratio == "16:9"
        assert spec.max_video_length_sec == 60
        assert spec.max_video_size_mb == 256.0
        assert spec.caption_max_length == 5000


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
        assert config.aspect_ratio is None
        assert config.max_file_size_mb is None

    def test_image_config_with_aspect_ratio(self):
        """Test image config with aspect ratio specified."""
        config = ImageTaskConfig(
            prompt="Test",
            size="1080x1920",
            aspect_ratio="9:16",
        )
        assert config.size == "1080x1920"
        assert config.aspect_ratio == "9:16"

    def test_image_config_with_file_size_limit(self):
        """Test image config with file size limit."""
        config = ImageTaskConfig(
            prompt="Test",
            size="1200x675",
            max_file_size_mb=5.0,
        )
        assert config.max_file_size_mb == 5.0

    def test_image_config_with_all_platform_fields(self):
        """Test image config with all platform-specific fields."""
        config = ImageTaskConfig(
            prompt="Instagram Story visual",
            size="1080x1920",
            aspect_ratio="9:16",
            max_file_size_mb=4.0,
        )
        assert config.size == "1080x1920"
        assert config.aspect_ratio == "9:16"
        assert config.max_file_size_mb == 4.0

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

    def test_image_config_with_reference_image_url(self):
        """Test image config with reference image URL."""
        config = ImageTaskConfig(
            prompt="Product shot based on reference",
            size="1080x1080",
            reference_image_url="https://storage.googleapis.com/bucket/ref.jpg"
        )
        assert config.reference_image_url == "https://storage.googleapis.com/bucket/ref.jpg"

    def test_image_config_without_reference_image_url(self):
        """Test image config without reference image defaults to None."""
        config = ImageTaskConfig(prompt="Regular image", size="1024x1024")
        assert config.reference_image_url is None


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
        assert config.aspect_ratio is None
        assert config.max_file_size_mb is None

    def test_video_config_with_aspect_ratio(self):
        """Test video config with aspect ratio specified."""
        config = VideoTaskConfig(
            prompt="Test",
            duration_sec=15,
            aspect_ratio="9:16",
        )
        assert config.duration_sec == 15
        assert config.aspect_ratio == "9:16"

    def test_video_config_with_file_size_limit(self):
        """Test video config with file size limit."""
        config = VideoTaskConfig(
            prompt="Test",
            duration_sec=60,
            max_file_size_mb=512.0,
        )
        assert config.max_file_size_mb == 512.0

    def test_video_config_with_all_platform_fields(self):
        """Test video config with all platform-specific fields."""
        config = VideoTaskConfig(
            prompt="Twitter video ad",
            duration_sec=140,
            aspect_ratio="16:9",
            max_file_size_mb=512.0,
        )
        assert config.duration_sec == 140
        assert config.aspect_ratio == "16:9"
        assert config.max_file_size_mb == 512.0

    def test_video_config_defaults(self):
        """Test default duration value."""
        config = VideoTaskConfig(prompt="Test prompt")
        assert config.duration_sec == 15

    def test_video_config_validation_min(self):
        """Test validation rejects duration < 5."""
        with pytest.raises(ValidationError):
            VideoTaskConfig(prompt="Test", duration_sec=3)

    def test_video_config_validation_max(self):
        """Test validation rejects duration > 600."""
        with pytest.raises(ValidationError):
            VideoTaskConfig(prompt="Test", duration_sec=601)


class TestTaskList:
    """Tests for TaskList model."""

    def test_valid_task_list_all_tasks(self):
        """Test task list with all task types."""
        task_list = TaskList(
            goal="Launch new feature",
            target_platforms=[Platform.INSTAGRAM_FEED, Platform.TWITTER],
            captions=CaptionTaskConfig(n=3, style="twitter"),
            image=ImageTaskConfig(prompt="Blue visual", size="1024x1024"),
            video=VideoTaskConfig(prompt="Demo video", duration_sec=20),
        )
        assert task_list.goal == "Launch new feature"
        assert task_list.target_platforms == [Platform.INSTAGRAM_FEED, Platform.TWITTER]
        assert task_list.captions is not None
        assert task_list.captions.n == 3
        assert task_list.image is not None
        assert task_list.image.prompt == "Blue visual"
        assert task_list.video is not None
        assert task_list.video.duration_sec == 20

    def test_task_list_requires_target_platforms(self):
        """Test that target_platforms is required."""
        with pytest.raises(ValidationError) as exc_info:
            TaskList(
                goal="Test goal",
                captions=CaptionTaskConfig(n=1),
            )
        assert "target_platforms" in str(exc_info.value).lower()

    def test_task_list_requires_at_least_one_platform(self):
        """Test that at least one platform must be selected."""
        with pytest.raises(ValidationError) as exc_info:
            TaskList(
                goal="Test goal",
                target_platforms=[],
                captions=CaptionTaskConfig(n=1),
            )
        error_msg = str(exc_info.value).lower()
        assert "target_platforms" in error_msg
        assert "at least 1" in error_msg

    def test_task_list_single_platform(self):
        """Test task list with single platform."""
        task_list = TaskList(
            goal="Instagram only campaign",
            target_platforms=[Platform.INSTAGRAM_FEED],
            captions=CaptionTaskConfig(n=5),
        )
        assert len(task_list.target_platforms) == 1
        assert task_list.target_platforms[0] == Platform.INSTAGRAM_FEED

    def test_task_list_multiple_platforms(self):
        """Test task list with multiple platforms."""
        platforms = [
            Platform.INSTAGRAM_FEED,
            Platform.INSTAGRAM_STORY,
            Platform.TWITTER,
            Platform.FACEBOOK,
            Platform.LINKEDIN,
        ]
        task_list = TaskList(
            goal="Multi-platform campaign",
            target_platforms=platforms,
            captions=CaptionTaskConfig(n=7),
            image=ImageTaskConfig(prompt="Product shot"),
        )
        assert len(task_list.target_platforms) == 5
        assert task_list.target_platforms == platforms

    def test_task_list_only_goal(self):
        """Test task list with only goal fails validation."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            TaskList(goal="Simple goal", target_platforms=[Platform.TWITTER])

        assert "At least one task" in str(exc_info.value)

    def test_task_list_partial_tasks(self):
        """Test task list with some tasks defined."""
        task_list = TaskList(
            goal="Partial tasks",
            target_platforms=[Platform.LINKEDIN],
            captions=CaptionTaskConfig(n=5),
        )
        assert task_list.target_platforms == [Platform.LINKEDIN]
        assert task_list.captions is not None
        assert task_list.image is None
        assert task_list.video is None

    def test_task_list_serialization(self):
        """Test that task list can be serialized to JSON."""
        task_list = TaskList(
            goal="Test",
            target_platforms=[Platform.LINKEDIN, Platform.FACEBOOK],
            captions=CaptionTaskConfig(n=2, style="linkedin"),
        )
        json_data = task_list.model_dump()
        assert json_data["goal"] == "Test"
        assert json_data["target_platforms"] == ["linkedin", "facebook"]
        assert json_data["captions"]["n"] == 2
        assert json_data["captions"]["style"] == "linkedin"

    def test_task_list_with_reference_image_url(self):
        """Test task list with reference image URL."""
        task_list = TaskList(
            goal="Product campaign with reference image",
            target_platforms=[Platform.INSTAGRAM_FEED],
            reference_image_url="https://storage.googleapis.com/bucket/product.jpg",
            captions=CaptionTaskConfig(n=3),
            image=ImageTaskConfig(
                prompt="Product shot",
                reference_image_url="https://storage.googleapis.com/bucket/product.jpg"
            ),
        )
        assert task_list.reference_image_url == "https://storage.googleapis.com/bucket/product.jpg"
        assert task_list.image.reference_image_url == "https://storage.googleapis.com/bucket/product.jpg"

    def test_task_list_without_reference_image_url(self):
        """Test task list without reference image defaults to None."""
        task_list = TaskList(
            goal="Regular campaign",
            target_platforms=[Platform.TWITTER],
            captions=CaptionTaskConfig(n=1),
        )
        assert task_list.reference_image_url is None


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
            target_platforms=[Platform.INSTAGRAM_FEED],
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
        assert job.task_list.target_platforms == [Platform.INSTAGRAM_FEED]
        assert job.captions == []
        assert job.images == []
        assert job.videos == []
        assert job.audit_logs == []
        assert job.approved_at is None

    def test_job_with_approval(self):
        """Test job with approval timestamp."""
        task_list = TaskList(
            goal="Test",
            target_platforms=[Platform.TWITTER],
            captions=CaptionTaskConfig(n=1)
        )
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
        task_list = TaskList(
            goal="Test",
            target_platforms=[Platform.FACEBOOK, Platform.LINKEDIN],
            captions=CaptionTaskConfig(n=2)
        )
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
            target_platforms=[Platform.YOUTUBE],
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
        task_list = TaskList(
            goal="Status test",
            target_platforms=[Platform.INSTAGRAM_STORY],
            captions=CaptionTaskConfig(n=1)
        )

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

    def test_job_with_reference_images(self):
        """Test job with reference images list."""
        task_list = TaskList(
            goal="Product campaign",
            target_platforms=[Platform.FACEBOOK],
            reference_image_url="https://storage.googleapis.com/bucket/ref.jpg",
            captions=CaptionTaskConfig(n=1),
        )
        job = Job(
            event_id="01JD4S3ABC",
            uid="user123",
            status=JobStatus.PENDING_APPROVAL,
            task_list=task_list,
            created_at="2025-11-08T10:00:00Z",
            updated_at="2025-11-08T10:00:00Z",
            reference_images=["https://storage.googleapis.com/bucket/ref.jpg"],
        )
        assert len(job.reference_images) == 1
        assert job.reference_images[0] == "https://storage.googleapis.com/bucket/ref.jpg"

    def test_job_without_reference_images(self):
        """Test job without reference images defaults to empty list."""
        task_list = TaskList(
            goal="Regular campaign",
            target_platforms=[Platform.LINKEDIN],
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
        assert job.reference_images == []


class TestBrandColor:
    """Tests for BrandColor model."""

    def test_valid_brand_color(self):
        """Test valid brand color configuration."""
        color = BrandColor(
            hex_code="FF5733",
            name="Primary Red",
            usage="primary"
        )
        assert color.hex_code == "FF5733"
        assert color.name == "Primary Red"
        assert color.usage == "primary"

    def test_brand_color_default_usage(self):
        """Test default usage value."""
        color = BrandColor(hex_code="000000", name="Black")
        assert color.usage == "general"

    def test_brand_color_validates_hex_format(self):
        """Test validation rejects invalid hex codes."""
        # Invalid: too short
        with pytest.raises(ValidationError):
            BrandColor(hex_code="FFF", name="White")

        # Invalid: contains non-hex characters
        with pytest.raises(ValidationError):
            BrandColor(hex_code="GGGGGG", name="Invalid")

        # Invalid: includes # prefix
        with pytest.raises(ValidationError):
            BrandColor(hex_code="#FF5733", name="Red")

    def test_brand_color_validates_usage(self):
        """Test validation rejects invalid usage values."""
        with pytest.raises(ValidationError):
            BrandColor(
                hex_code="FF5733",
                name="Red",
                usage="invalid_usage"
            )

    def test_brand_color_accepts_all_valid_usages(self):
        """Test all valid usage values are accepted."""
        valid_usages = ["primary", "accent", "background", "general"]
        for usage in valid_usages:
            color = BrandColor(
                hex_code="000000",
                name="Test",
                usage=usage
            )
            assert color.usage == usage


class TestBrandStyle:
    """Tests for BrandStyle model."""

    def test_valid_brand_style(self):
        """Test valid brand style configuration."""
        style = BrandStyle(
            colors=[
                BrandColor(hex_code="FF5733", name="Primary Red", usage="primary"),
                BrandColor(hex_code="33FF57", name="Accent Green", usage="accent"),
            ],
            tone=BrandTone.PROFESSIONAL,
            tagline="Innovation starts here"
        )
        assert len(style.colors) == 2
        assert style.tone == BrandTone.PROFESSIONAL
        assert style.tagline == "Innovation starts here"

    def test_brand_style_default_tone(self):
        """Test default tone is PROFESSIONAL."""
        style = BrandStyle(
            colors=[BrandColor(hex_code="000000", name="Black")]
        )
        assert style.tone == BrandTone.PROFESSIONAL

    def test_brand_style_optional_fields(self):
        """Test optional logo_url and tagline fields."""
        style = BrandStyle(
            colors=[BrandColor(hex_code="000000", name="Black")],
            tone=BrandTone.CASUAL
        )
        assert style.logo_url is None
        assert style.tagline is None

    def test_brand_style_requires_at_least_one_color(self):
        """Test validation requires at least one color."""
        with pytest.raises(ValidationError):
            BrandStyle(colors=[], tone=BrandTone.PLAYFUL)

    def test_brand_style_max_five_colors(self):
        """Test validation limits to 5 colors."""
        colors = [
            BrandColor(hex_code=f"{i:02d}0000", name=f"Color {i}")
            for i in range(6)
        ]
        with pytest.raises(ValidationError):
            BrandStyle(colors=colors, tone=BrandTone.LUXURY)

    def test_brand_style_tagline_max_length(self):
        """Test tagline max length validation."""
        with pytest.raises(ValidationError):
            BrandStyle(
                colors=[BrandColor(hex_code="000000", name="Black")],
                tagline="x" * 101  # Exceeds 100 character limit
            )

    def test_brand_style_rejects_multiple_primary_colors(self):
        """Test validation rejects more than one primary color."""
        with pytest.raises(ValidationError, match="Only one color can be marked as primary"):
            BrandStyle(
                colors=[
                    BrandColor(hex_code="FF0000", name="Red 1", usage="primary"),
                    BrandColor(hex_code="0000FF", name="Blue 1", usage="primary"),
                ],
                tone=BrandTone.CASUAL
            )

    def test_brand_style_rejects_tagline_with_html(self):
        """Test validation rejects tagline with HTML tags to prevent XSS."""
        with pytest.raises(ValidationError, match="Tagline cannot contain HTML tags"):
            BrandStyle(
                colors=[BrandColor(hex_code="000000", name="Black")],
                tone=BrandTone.PROFESSIONAL,
                tagline="<script>alert('xss')</script>"
            )

    def test_brand_style_all_tones(self):
        """Test all brand tone values are valid."""
        tones = [
            BrandTone.PROFESSIONAL,
            BrandTone.CASUAL,
            BrandTone.PLAYFUL,
            BrandTone.LUXURY,
            BrandTone.TECHNICAL,
        ]
        for tone in tones:
            style = BrandStyle(
                colors=[BrandColor(hex_code="000000", name="Black")],
                tone=tone
            )
            assert style.tone == tone


class TestTaskListWithBrandStyle:
    """Tests for TaskList with brand_style field."""

    def test_task_list_with_brand_style(self):
        """Test TaskList with brand style."""
        brand_style = BrandStyle(
            colors=[BrandColor(hex_code="1A1A1A", name="Charcoal", usage="primary")],
            tone=BrandTone.LUXURY,
            tagline="Elevate your experience"
        )
        task_list = TaskList(
            goal="Launch premium product",
            target_platforms=[Platform.INSTAGRAM_FEED],
            brand_style=brand_style,
            image=ImageTaskConfig(prompt="Elegant product shot", size="1080x1080")
        )
        assert task_list.brand_style is not None
        assert task_list.brand_style.tone == BrandTone.LUXURY
        assert len(task_list.brand_style.colors) == 1

    def test_task_list_without_brand_style(self):
        """Test TaskList works without brand style (optional)."""
        task_list = TaskList(
            goal="Generic campaign",
            target_platforms=[Platform.TWITTER],
            captions=CaptionTaskConfig(n=3)
        )
        assert task_list.brand_style is None

    def test_task_list_brand_style_serialization(self):
        """Test TaskList with brand style serializes correctly."""
        brand_style = BrandStyle(
            colors=[BrandColor(hex_code="FF5733", name="Red")],
            tone=BrandTone.PLAYFUL
        )
        task_list = TaskList(
            goal="Fun campaign",
            target_platforms=[Platform.FACEBOOK],
            brand_style=brand_style,
            captions=CaptionTaskConfig(n=5)
        )

        # Serialize
        data = task_list.model_dump()
        assert "brand_style" in data
        assert data["brand_style"]["tone"] == "playful"

        # Deserialize
        reconstructed = TaskList(**data)
        assert reconstructed.brand_style.tone == BrandTone.PLAYFUL
        assert reconstructed.brand_style.colors[0].hex_code == "FF5733"
