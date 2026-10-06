import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.post import PostStatus, PostType
from app.schemas.category import CategorySummary
from app.schemas.media import PostImageResponse


class AuthorSummary(BaseModel):
    """Safe public representation of post author."""

    id: uuid.UUID
    name: str
    university_verified: bool
    profile_image_key: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PostCreateRequest(BaseModel):
    """Payload to create a new marketplace post."""

    model_config = ConfigDict(str_strip_whitespace=True)

    type: PostType = Field(..., description="PostType: OFFER or REQUEST")
    category_id: uuid.UUID = Field(..., description="Category UUID")
    title: str = Field(..., min_length=3, max_length=255, description="Listing title")
    description: str = Field(..., min_length=5, description="Detailed item or request description")
    price: Decimal | None = Field(default=None, description="Listing price or requested budget")
    price_unit: str | None = Field(
        default=None,
        max_length=50,
        description="Optional unit e.g. per hour, per day",
    )

    @model_validator(mode="after")
    def validate_price_for_type(self) -> "PostCreateRequest":
        if self.type == PostType.OFFER:
            if self.price is None:
                raise ValueError("Price is required for an OFFER post.")
            if self.price < Decimal("0.00"):
                raise ValueError("Price cannot be negative.")
        elif self.price is not None and self.price < Decimal("0.00"):
            raise ValueError("Price/budget cannot be negative.")
        return self


class PostUpdateRequest(BaseModel):
    """Payload to update an existing draft or published post."""

    model_config = ConfigDict(str_strip_whitespace=True)

    category_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=5)
    price: Decimal | None = None
    price_unit: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_price(self) -> "PostUpdateRequest":
        if self.price is not None and self.price < Decimal("0.00"):
            raise ValueError("Price cannot be negative.")
        return self


class PostResponse(BaseModel):
    """Public details of a marketplace post."""

    id: uuid.UUID
    author: AuthorSummary
    category: CategorySummary
    type: PostType
    status: PostStatus
    title: str
    description: str
    price: Decimal | None = None
    price_unit: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    images: list["PostImageResponse"] = Field(default_factory=list)
    whatsapp_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PostListResponse(BaseModel):
    """Paginated collection of posts."""

    items: list[PostResponse]
    total: int
    page: int
    page_size: int
    pages: int
