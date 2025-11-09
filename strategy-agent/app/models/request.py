"""API request models."""

from pydantic import BaseModel, Field


class StrategizeRequest(BaseModel):
    """Request model for /strategize endpoint."""

    goal: str = Field(
        description="High-level marketing goal",
        min_length=10,
        max_length=500,
        examples=["Launch awareness campaign for new AI feature"],
    )
    uid: str = Field(
        description="User ID from Firebase Auth",
        examples=["user_abc123"],
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
