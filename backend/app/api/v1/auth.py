from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppException
from app.core.limiter import rate_limiter
from app.core.proxy import get_client_ip
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
    ResendVerificationRequest,
    TokenResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.services.legal import get_current_legal_document, record_user_consent

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register student account",
)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Register a new student with university domain check and verification code.

    Enforces IP-based rate limiting designed for university NATs.
    """
    client_ip = get_client_ip(request)
    rate_limiter.check_registration_rate_limit(client_ip)

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

    # Enforce legal consent server-side (cannot be bypassed by direct API calls)
    if not data.accepted_terms or not data.accepted_privacy:
        raise AppException(
            code="LEGAL_CONSENT_REQUIRED",
            message="You must accept the Terms & Conditions and Privacy Policy.",
            status_code=status.HTTP_400_BAD_REQUEST,
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

    # Server-side determination of active legal document versions
    terms_doc = get_current_legal_document(db, "TERMS")
    privacy_doc = get_current_legal_document(db, "PRIVACY")
    user_agent = request.headers.get("user-agent")

    record_user_consent(
        db=db,
        user_id=user.id,
        document_type="TERMS",
        version=terms_doc.version if terms_doc else "1.0",
        ip_address=client_ip,
        user_agent=user_agent[:512] if user_agent else None,
    )
    record_user_consent(
        db=db,
        user_id=user.id,
        document_type="PRIVACY",
        version=privacy_doc.version if privacy_doc else "1.0",
        ip_address=client_ip,
        user_agent=user_agent[:512] if user_agent else None,
    )

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
    request: Request,
    db: Session = Depends(get_db),
) -> VerifyResponse:
    """Verify university student email with provided OTP.

    Protected by IP and email rate limiting. Limits verification cycle to max 5 attempts;
    invalidates code upon exceeding maximum attempts without revealing account presence.
    """
    client_ip = get_client_ip(request)
    email_clean = data.email.strip().lower()
    rate_limiter.check_verify_rate_limit(client_ip, email_clean)

    user = db.scalar(select(User).where(User.email == email_clean))
    if user is None:
        raise AppException(
            code="INVALID_OR_EXPIRED_CODE",
            message="Verification code is invalid or has expired.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    now = datetime.now(UTC)
    stmt = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user.id,
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

    # Track attempts on this specific verification code cycle
    attempts = rate_limiter.increment_otp_attempts(str(verification.id))

    if attempts > 5:
        # Invalidate the OTP in the database
        verification.used_at = now
        db.commit()
        raise AppException(
            code="MAX_ATTEMPTS_EXCEEDED",
            message=(
                "Maximum verification attempts exceeded. "
                "This verification code has been invalidated. Please request a new code."
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if verification.code != data.code.strip():
        if attempts == 5:
            # 5th failed attempt invalidates the code
            verification.used_at = now
            db.commit()
            raise AppException(
                code="MAX_ATTEMPTS_EXCEEDED",
                message=(
                    "Maximum verification attempts exceeded. "
                    "This verification code has been invalidated. Please request a new code."
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        raise AppException(
            code="INVALID_OR_EXPIRED_CODE",
            message="Verification code is invalid or has expired.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Correct code provided
    verification.used_at = now
    user.university_verified = True
    db.commit()
    rate_limiter.reset_otp_attempts(str(verification.id))

    return VerifyResponse(
        message="University email verified successfully.",
        university_verified=True,
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification OTP",
)
def resend_verification(
    data: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Request a fresh university email verification code.

    Enforces a 60-second cooldown and hourly limits per IP and account.
    Returns generic response to prevent account enumeration.
    """
    client_ip = get_client_ip(request)
    email_clean = data.email.strip().lower()
    rate_limiter.check_resend_rate_limit(client_ip, email_clean)

    user = db.scalar(select(User).where(User.email == email_clean))
    if user and not user.university_verified:
        code = generate_verification_code()
        delta = timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
        expires_at = datetime.now(UTC) + delta
        verification = EmailVerificationCode(
            user_id=user.id,
            code=code,
            expires_at=expires_at,
        )
        db.add(verification)
        db.commit()

    return MessageResponse(
        message=(
            "If this account exists and is unverified, "
            "a new verification code has been dispatched."
        )
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate student user and return short-lived access and long-lived refresh tokens.

    Protected against brute force via IP and account-level failure tracking.
    """
    client_ip = get_client_ip(request)
    email_clean = data.email.strip().lower()
    rate_limiter.check_login_rate_limit(client_ip, email_clean)

    user = db.scalar(select(User).where(User.email == email_clean))

    if user is None or not verify_password(data.password, user.hashed_password):
        rate_limiter.record_login_failure(client_ip, email_clean)
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

    # Successful authentication resets the failure count for this email
    rate_limiter.record_login_success(email_clean)

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
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange valid revocable refresh token for fresh access token."""
    client_ip = get_client_ip(request)
    token_hash = hash_token(data.refresh_token)
    rate_limiter.check_refresh_rate_limit(client_ip, token_hash)

    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise AppException(
            code="TOKEN_INVALID",
            message="Provided token is not a refresh token.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

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
