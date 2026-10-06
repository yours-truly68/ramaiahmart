import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportReason, ReportStatus


class ReportCreateRequest(BaseModel):
    """Schema for submitting a report against a marketplace post."""

    post_id: uuid.UUID
    reason: ReportReason
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional detailed explanation from the reporter",
    )


class ReportResponse(BaseModel):
    """Schema returned after a report is recorded and reviewed."""

    id: uuid.UUID
    post_id: uuid.UUID
    reporter_id: uuid.UUID
    reason: ReportReason
    description: str | None = None
    status: ReportStatus
    ai_reviewed: bool
    ai_decision: str | None = None
    ai_reason: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
