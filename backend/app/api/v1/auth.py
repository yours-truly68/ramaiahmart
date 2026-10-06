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
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.auth import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services.legal import get_current_legal_document, record_user_consent
from app.services.lifecycle import record_user_activity

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
    """Register a new student with university domain check.

    V1 policy: RamaiahMart does not send authentication emails. Registration
    with a valid @msrit.edu address is sufficient to create and use an account;
    no separate email-verification step exists. Passwords are hashed with bcrypt
    and never stored, logged, or returned in plaintext.

    Enforces IP-based rate limiting designed for university NATs.
    """
    client_ip = get_client_ip(request)
    rate_limiter.check_registration_rate_limit(client_ip)

    email_clean = data.email.strip().lower()

    if not settings.is_university_email(email_clean):
        raise AppException(
            code="INVALID_UNIVERSITY_EMAIL",
            message="Registration is restricted to @msrit.edu email addresses.",
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
        # V1: a valid @msrit.edu registration is sufficient. The column is kept
        # for a future automated email-verification migration, but it never
        # blocks normal V1 operation.
        university_verified=True,
        is_active=True,
    )
    db.add(user)
    db.flush()

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

    return RegisterResponse(
        message="Registration successful. You can log in with your @msrit.edu account.",
        email=user.email,
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
    A successful login during the deletion grace period automatically cancels
    the pending deletion (counts as meaningful activity).
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

    now = datetime.now(UTC)
    user.last_login_at = now
    # Meaningful activity: reactivates INACTIVE accounts and cancels pending deletion.
    record_user_activity(user, db, commit=False)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Persist refresh token hash
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
    """Exchange valid revocable refresh token for fresh access token.

    Token refresh is NOT meaningful activity: it never updates last_activity_at,
    never reactivates INACTIVE accounts, and never cancels pending deletions.
    """
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
    }
