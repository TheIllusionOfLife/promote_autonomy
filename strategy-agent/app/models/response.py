"""API response models."""

from pydantic import BaseModel, Field
from promote_autonomy_shared.schemas import Job, JobStatus


class StrategizeResponse(BaseModel):
    """Response model for /strategize endpoint."""

    event_id: str = Field(description="Created job event ID")
    status: JobStatus = Field(description="Job status (pending_approval)")
    message: str = Field(description="Human-readable message")


class ApproveResponse(BaseModel):
    """Response model for /approve endpoint."""

    event_id: str = Field(description="Approved job event ID")
    status: JobStatus = Field(description="Updated job status (processing)")
    message: str = Field(description="Human-readable message")
    published: bool = Field(
        description="Whether task was published to Pub/Sub",
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error type")
    detail: str = Field(description="Error details")
    event_id: str | None = Field(default=None, description="Event ID if available")
