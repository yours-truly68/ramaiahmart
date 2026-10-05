import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    """Category representation."""

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategorySummary(BaseModel):
    """Compact category details embedded in listing responses."""

    id: uuid.UUID
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class CategoryCreateRequest(BaseModel):
    """Admin/seed category creation schema."""

    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
