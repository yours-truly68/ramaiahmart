import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LegalDocumentResponse(BaseModel):
    """Platform legal document representation."""

    id: uuid.UUID
    document_type: str
    version: str
    title: str
    content: str
    effective_at: datetime
    published_at: datetime
    is_current: bool

    model_config = {"from_attributes": True}


class ConsentItemStatus(BaseModel):
    """User acceptance state for a specific document category."""

    current_version: str
    accepted_version: str | None = None
    accepted: bool
    accepted_at: datetime | None = None


class UserConsentStatusResponse(BaseModel):
    """Consolidated legal consent status for authenticated user."""

    terms: ConsentItemStatus
    privacy: ConsentItemStatus


class RecordConsentRequest(BaseModel):
    """Input for accepting or re-consenting to an active legal document."""

    document_type: str = Field(..., description="'TERMS' or 'PRIVACY'")


class RecordConsentResponse(BaseModel):
    """Outcome of recording legal consent."""

    message: str
    document_type: str
    version: str
    accepted_at: datetime
