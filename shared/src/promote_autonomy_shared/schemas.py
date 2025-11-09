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


class VideoTaskConfig(BaseModel):
    """Configuration for video generation task."""

    prompt: str = Field(description="Text prompt for video generation")
    duration_sec: int = Field(
        default=15,
        ge=5,
        le=60,
        description="Video duration in seconds",
    )


class TaskList(BaseModel):
    """Task list defining what assets to generate."""

    goal: str = Field(description="High-level marketing goal")
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
    def at_least_one_task(self):
        """Validate that at least one task type is specified."""
        if not (self.captions or self.image or self.video):
            raise ValueError(
                "At least one task (captions, image, or video) must be specified. "
                "Cannot create a job with no assets to generate."
            )
        return self

    model_config = {"json_schema_extra": {"example": {
        "goal": "Increase awareness of new feature",
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
    }}}
