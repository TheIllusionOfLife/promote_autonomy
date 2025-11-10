"""Core data schemas for Promote Autonomy."""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class JobStatus(str, Enum):
    """Status values for a job in Firestore."""

    PENDING_APPROVAL = "pending_approval"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class BrandTone(str, Enum):
    """Brand communication tone for consistent messaging."""

    PROFESSIONAL = "professional"  # Corporate, formal language
    CASUAL = "casual"  # Friendly, approachable tone
    PLAYFUL = "playful"  # Fun, energetic, emoji-rich
    LUXURY = "luxury"  # Elegant, sophisticated
    TECHNICAL = "technical"  # Precise, expert terminology


class BrandColor(BaseModel):
    """Brand color specification with hex code and usage context."""

    hex_code: str = Field(
        description="6-digit hex color code without # prefix (e.g., 'FF5733')",
        pattern=r"^[0-9A-Fa-f]{6}$",
    )
    name: str = Field(
        description="Human-readable color name (e.g., 'Primary Red')",
        min_length=1,
        max_length=50,
    )
    usage: str = Field(
        default="general",
        description="Usage context: 'primary', 'accent', 'background', or 'general'",
    )

    @field_validator("usage")
    @classmethod
    def validate_usage(cls, v: str) -> str:
        """Validate usage is one of the allowed values."""
        allowed = ["primary", "accent", "background", "general"]
        if v not in allowed:
            raise ValueError(
                f"Invalid usage '{v}'. Must be one of: {', '.join(allowed)}"
            )
        return v


class BrandStyle(BaseModel):
    """Brand style guide configuration for consistent asset generation."""

    colors: list[BrandColor] = Field(
        description="Brand colors (1-5 colors)",
        min_length=1,
        max_length=5,
    )
    tone: BrandTone = Field(
        default=BrandTone.PROFESSIONAL,
        description="Brand communication tone",
    )
    logo_url: Optional[str] = Field(
        default=None,
        description="URL to brand logo in Cloud Storage (optional)",
    )
    tagline: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Brand tagline to include in captions (optional)",
    )


class Platform(str, Enum):
    """Supported social media platforms."""

    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_STORY = "instagram_story"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"


class PlatformSpec(BaseModel):
    """Platform-specific asset requirements."""

    platform: Platform = Field(description="Target platform")
    image_size: str = Field(description="Image size in WIDTHxHEIGHT format")
    image_aspect_ratio: str = Field(description="Image aspect ratio (e.g., '1:1', '16:9')")
    max_image_size_mb: float = Field(description="Maximum image file size in MB")
    video_size: str = Field(description="Video resolution in WIDTHxHEIGHT format")
    video_aspect_ratio: str = Field(description="Video aspect ratio (e.g., '16:9', '9:16')")
    max_video_length_sec: int = Field(description="Maximum video length in seconds")
    max_video_size_mb: float = Field(description="Maximum video file size in MB")
    caption_max_length: int = Field(description="Maximum caption length in characters")


# Platform-specific specifications
PLATFORM_SPECS: dict[Platform, PlatformSpec] = {
    Platform.INSTAGRAM_FEED: PlatformSpec(
        platform=Platform.INSTAGRAM_FEED,
        image_size="1080x1080",
        image_aspect_ratio="1:1",
        max_image_size_mb=4.0,
        video_size="1080x1080",
        video_aspect_ratio="1:1",
        max_video_length_sec=60,
        max_video_size_mb=4.0,
        caption_max_length=2200,
    ),
    Platform.INSTAGRAM_STORY: PlatformSpec(
        platform=Platform.INSTAGRAM_STORY,
        image_size="1080x1920",
        image_aspect_ratio="9:16",
        max_image_size_mb=4.0,
        video_size="1080x1920",
        video_aspect_ratio="9:16",
        max_video_length_sec=15,
        max_video_size_mb=4.0,
        caption_max_length=2200,
    ),
    Platform.TWITTER: PlatformSpec(
        platform=Platform.TWITTER,
        image_size="1200x675",
        image_aspect_ratio="16:9",
        max_image_size_mb=5.0,
        video_size="1280x720",
        video_aspect_ratio="16:9",
        max_video_length_sec=140,
        max_video_size_mb=512.0,
        caption_max_length=280,
    ),
    Platform.FACEBOOK: PlatformSpec(
        platform=Platform.FACEBOOK,
        image_size="1200x630",
        image_aspect_ratio="1.91:1",
        max_image_size_mb=8.0,
        video_size="1280x720",
        video_aspect_ratio="16:9",
        max_video_length_sec=240,
        max_video_size_mb=4096.0,
        caption_max_length=63206,
    ),
    Platform.LINKEDIN: PlatformSpec(
        platform=Platform.LINKEDIN,
        image_size="1200x627",
        image_aspect_ratio="1.91:1",
        max_image_size_mb=5.0,
        video_size="1280x720",
        video_aspect_ratio="16:9",
        max_video_length_sec=600,
        max_video_size_mb=5120.0,
        caption_max_length=3000,
    ),
    Platform.YOUTUBE: PlatformSpec(
        platform=Platform.YOUTUBE,
        image_size="1280x720",
        image_aspect_ratio="16:9",
        max_image_size_mb=2.0,
        video_size="1920x1080",
        video_aspect_ratio="16:9",
        max_video_length_sec=60,
        max_video_size_mb=256.0,
        caption_max_length=5000,
    ),
}


class CaptionTaskConfig(BaseModel):
    """Configuration for caption generation task."""

    n: int = Field(ge=1, le=10, description="Number of captions to generate")
    style: str = Field(
        default="engaging",
        description="Caption style (e.g., 'engaging', 'twitter', 'linkedin')",
    )


class ImageTaskConfig(BaseModel):
    """Configuration for image generation task."""

    prompt: str = Field(description="Text prompt for image generation")
    size: str = Field(
        default="1024x1024",
        description="Image size (e.g., '1024x1024', '1024x1792')",
    )
    aspect_ratio: Optional[str] = Field(
        default=None,
        description="Target aspect ratio (e.g., '1:1', '16:9', '9:16')",
    )
    max_file_size_mb: Optional[float] = Field(
        default=None,
        description="Maximum file size in megabytes",
    )
    reference_image_url: Optional[str] = Field(
        default=None,
        description="URL to reference product image for context-aware generation",
    )

    @field_validator("size")
    @classmethod
    def validate_size_format(cls, v: str) -> str:
        """Validate size format is WIDTHxHEIGHT with positive integers."""
        if not re.match(r"^\d+x\d+$", v):
            raise ValueError(
                f"Invalid size format '{v}'. Expected format: 'WIDTHxHEIGHT' "
                "(e.g., '1024x1024', '1024x1792')"
            )

        # Parse and validate positive dimensions
        width, height = map(int, v.split("x"))
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Invalid dimensions: {width}x{height}. "
                "Width and height must be positive integers."
            )

        return v

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate aspect ratio format is N:M or N.N:M."""
        if v is None:
            return v
        if not re.match(r"^\d+(?:\.\d+)?:\d+(?:\.\d+)?$", v):
            raise ValueError(
                f"Invalid aspect ratio format '{v}'. Expected format: 'N:M' "
                "(e.g., '1:1', '16:9', '1.91:1')"
            )
        return v


class VideoTaskConfig(BaseModel):
    """Configuration for video generation task."""

    prompt: str = Field(description="Text prompt for video generation")
    duration_sec: int = Field(
        default=15,
        ge=4,
        le=600,
        description="Video duration in seconds (platform limits vary: Instagram Story 15s, Twitter 140s, LinkedIn 600s)",
    )
    aspect_ratio: Optional[str] = Field(
        default=None,
        description="Target aspect ratio (e.g., '16:9', '9:16', '1:1')",
    )
    max_file_size_mb: Optional[float] = Field(
        default=None,
        description="Maximum file size in megabytes",
    )

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate aspect ratio format is N:M or N.N:M."""
        if v is None:
            return v
        if not re.match(r"^\d+(?:\.\d+)?:\d+(?:\.\d+)?$", v):
            raise ValueError(
                f"Invalid aspect ratio format '{v}'. Expected format: 'N:M' "
                "(e.g., '1:1', '16:9', '1.91:1')"
            )
        return v


class TaskList(BaseModel):
    """Task list defining what assets to generate."""

    goal: str = Field(description="High-level marketing goal")
    target_platforms: list[Platform] = Field(
        description="Target social media platforms for this campaign",
        min_length=1,
    )
    brand_style: Optional[BrandStyle] = Field(
        default=None,
        description="Brand style guide for consistent asset generation (optional)",
    )
    reference_image_url: Optional[str] = Field(
        default=None,
        description="URL to uploaded reference product image",
    )
    captions: Optional[CaptionTaskConfig] = Field(
        default=None,
        description="Caption generation configuration",
    )
    image: Optional[ImageTaskConfig] = Field(
        default=None,
        description="Image generation configuration",
    )
    video: Optional[VideoTaskConfig] = Field(
        default=None,
        description="Video generation configuration",
    )

    @model_validator(mode='after')
    def validate_task_list(self):
        """Validate task list constraints."""
        # At least one task must be specified
        if not (self.captions or self.image or self.video):
            raise ValueError(
                "At least one task (captions, image, or video) must be specified. "
                "Cannot create a job with no assets to generate."
            )

        return self

    model_config = {"json_schema_extra": {"example": {
        "goal": "Increase awareness of new feature",
        "target_platforms": ["instagram_feed", "twitter"],
        "captions": {"n": 3, "style": "twitter"},
        "image": {
            "prompt": "Clean blue modern promo visual",
            "size": "1024x1024",
        },
    }}}


class Job(BaseModel):
    """Firestore job document model."""

    event_id: str = Field(description="Unique job identifier (ULID)")
    uid: str = Field(description="User ID from Firebase Auth")
    status: JobStatus = Field(description="Current job status")
    task_list: TaskList = Field(description="Task list to execute")
    created_at: str = Field(description="ISO 8601 timestamp of creation")
    updated_at: str = Field(description="ISO 8601 timestamp of last update")
    approved_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp of approval",
    )
    captions: list[str] = Field(
        default_factory=list,
        description="URLs to JSON files in Cloud Storage containing generated captions",
    )
    images: list[str] = Field(
        default_factory=list,
        description="Image URLs in Cloud Storage",
    )
    videos: list[str] = Field(
        default_factory=list,
        description="Video URLs in Cloud Storage",
    )
    audit_logs: list[str] = Field(
        default_factory=list,
        description="Optional approval audit trail",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages about asset generation (e.g., file size limits exceeded)",
    )
    reference_images: list[str] = Field(
        default_factory=list,
        description="URLs to uploaded reference images in Cloud Storage",
    )

    model_config = {"json_schema_extra": {"example": {
        "event_id": "01JD4S3ABCXYZ",
        "uid": "user123",
        "status": "pending_approval",
        "task_list": {
            "goal": "Launch new feature",
            "captions": {"n": 3, "style": "twitter"},
        },
        "created_at": "2025-11-08T10:00:00Z",
        "updated_at": "2025-11-08T10:00:00Z",
        "captions": [],
        "images": [],
        "videos": [],
        "audit_logs": [],
        "warnings": [],
    }}}
