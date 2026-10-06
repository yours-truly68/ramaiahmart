import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppException


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_token(
    subject: str | uuid.UUID,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    """Create signed JWT token."""
    now = datetime.now(UTC)
    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create short-lived access token."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(subject, "access", delta)


def create_refresh_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create long-lived refresh token."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(subject, "refresh", delta)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT token signature and expiry."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise AppException(
            code="TOKEN_EXPIRED",
            message="Token has expired.",
            status_code=401,
        ) from None
    except jwt.InvalidTokenError:
        raise AppException(
            code="TOKEN_INVALID",
            message="Invalid authentication token.",
            status_code=401,
        ) from None


def hash_token(token: str) -> str:
    """Produce SHA-256 hash of token for lookup/revocation."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
