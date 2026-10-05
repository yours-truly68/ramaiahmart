from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Retrieve authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update own user profile",
)
def update_me(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update profile information of the authenticated user."""
    if data.name is not None:
        current_user.name = data.name.strip()
    if data.bio is not None:
        current_user.bio = data.bio.strip()
    if data.profile_image_key is not None:
        current_user.profile_image_key = data.profile_image_key.strip()

    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)
