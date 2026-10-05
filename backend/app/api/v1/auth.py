from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_verification_code,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.auth import EmailVerificationCode, RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerifyRequest,
    VerifyResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register student account",
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Register a new student with university domain check and verification code."""
    email_clean = data.email.strip().lower()

    if not settings.is_university_email(email_clean):
        raise AppException(
            code="INVALID_UNIVERSITY_EMAIL",
            message="Registration is restricted to authorized university email domains.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    existing_user = db.scalar(select(User).where(User.email == email_clean))
    if existing_user is not None:
        raise AppException(
            code="EMAIL_ALREADY_EXISTS",
            message="An account with this email address already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )

    hashed_pw = hash_password(data.password)
    user = User(
        email=email_clean,
        name=data.name.strip(),
        hashed_password=hashed_pw,
        university_verified=False,
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Generate verification OTP
    code = generate_verification_code()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
    verification = EmailVerificationCode(
        user_id=user.id,
        code=code,
        expires_at=expires_at,
    )
    db.add(verification)
    db.commit()

    # In dev/test return verification code in payload for automated/local testing
    expose_code = code if (settings.DEBUG or settings.APP_ENV != "production") else None

    return RegisterResponse(
        message="Registration successful. Please verify your university email.",
        email=user.email,
        verification_code=expose_code,
    )


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify university email",
)
def verify(
    data: VerifyRequest,
    db: Session = Depends(get_db),
) -> VerifyResponse:
    """Verify university student email with provided OTP."""
    email_clean = data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_clean))
    if user is None:
        raise AppException(
            code="USER_NOT_FOUND",
            message="No account found with this email address.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    now = datetime.now(UTC)
    stmt = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
            EmailVerificationCode.code == data.code.strip(),
            EmailVerificationCode.used_at.is_(None),
            EmailVerificationCode.expires_at > now,
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )
    verification = db.scalar(stmt)
    if verification is None:
        raise AppException(
            code="INVALID_OR_EXPIRED_CODE",
            message="Verification code is invalid or has expired.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    verification.used_at = now
    user.university_verified = True
    db.commit()

    return VerifyResponse(
        message="University email verified successfully.",
        university_verified=True,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate student user and return short-lived access and long-lived refresh tokens."""
    email_clean = data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_clean))

    if user is None or not verify_password(data.password, user.hashed_password):
        raise AppException(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        raise AppException(
            code="USER_INACTIVE",
            message="Your account has been deactivated.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Persist refresh token hash
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=expires_at,
    )
    db.add(db_refresh)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
def refresh(
    data: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange valid revocable refresh token for fresh access token."""
    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise AppException(
            code="TOKEN_INVALID",
            message="Provided token is not a refresh token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token_hash = hash_token(data.refresh_token)
    now = datetime.now(UTC)

    stored_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )

    if stored_token is None:
        raise AppException(
            code="TOKEN_REVOKED_OR_EXPIRED",
            message="Refresh token has been revoked or expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = db.scalar(select(User).where(User.id == stored_token.user_id))
    if user is None or not user.is_active:
        raise AppException(
            code="USER_INACTIVE",
            message="User associated with token is not active.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    new_access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=data.refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke refresh token and logout",
)
def logout(
    data: LogoutRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Revoke refresh token, terminating the session."""
    token_hash = hash_token(data.refresh_token)
    stored_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )

    if stored_token is not None:
        stored_token.revoked_at = datetime.now(UTC)
        db.commit()

    return MessageResponse(message="Logged out successfully.")


@router.get("/config", summary="Public registration requirements")
def auth_config() -> dict:
    return {
        "allowed_email_domains": settings.ALLOWED_EMAIL_DOMAINS,
        "password_min_length": 8,
        "verification_code_available": settings.DEBUG or settings.APP_ENV != "production",
        "email_delivery_available": False,
    }
