"""API request models."""

from typing import Optional

from pydantic import BaseModel, Field
from promote_autonomy_shared.schemas import BrandStyle, Platform


class StrategizeRequest(BaseModel):
    """Request model for /strategize endpoint."""

    goal: str = Field(
        description="High-level marketing goal",
        min_length=10,
        max_length=500,
        examples=["Launch awareness campaign for new AI feature"],
    )
    target_platforms: list[Platform] = Field(
        description="Target social media platforms for this campaign",
        min_length=1,
        examples=[["instagram_feed", "twitter"]],
    )
    uid: str = Field(
        description="User ID from Firebase Auth",
        examples=["user_abc123"],
    )
    brand_style: Optional[BrandStyle] = Field(
        default=None,
        description="Brand style guide for consistent asset generation (optional)",
    )


class ApproveRequest(BaseModel):
    """Request model for /approve endpoint."""

    event_id: str = Field(
        description="Job event ID to approve",
        examples=["01JD4S3ABCXYZ"],
    )
    uid: str = Field(
        description="User ID from Firebase Auth",
        examples=["user_abc123"],
    )
