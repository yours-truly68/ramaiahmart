import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer access token and return authenticated user."""
    if credentials is None:
        raise AppException(
            code="UNAUTHORIZED",
            message="Authentication credentials were not provided.",
            status_code=401,
        )

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AppException(
            code="TOKEN_INVALID",
            message="Invalid token type.",
            status_code=401,
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppException(
            code="TOKEN_INVALID",
            message="Missing subject claim in token.",
            status_code=401,
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise AppException(
            code="TOKEN_INVALID",
            message="Invalid user identifier in token.",
            status_code=401,
        ) from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise AppException(
            code="USER_NOT_FOUND",
            message="User associated with token no longer exists.",
            status_code=401,
        )

    if not user.is_active:
        raise AppException(
            code="USER_INACTIVE",
            message="User account is deactivated.",
            status_code=403,
        )

    return user


def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is authenticated and verified student."""
    if not current_user.university_verified:
        raise AppException(
            code="FORBIDDEN_UNVERIFIED",
            message="University email verification is required to perform this action.",
            status_code=403,
        )
    return current_user
