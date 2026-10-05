from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """User registration input."""

    email: str = Field(..., description="University email address")
    password: str = Field(..., min_length=8, description="Account password (min 8 chars)")
    name: str = Field(..., min_length=2, max_length=255, description="Full name")


class RegisterResponse(BaseModel):
    """Registration output."""

    message: str
    email: str
    verification_code: str | None = Field(
        default=None,
        description="Verification OTP (provided for development convenience)",
    )


class VerifyRequest(BaseModel):
    """University email verification input."""

    email: str = Field(..., description="Registered email address")
    code: str = Field(..., min_length=6, max_length=64, description="Verification OTP")


class VerifyResponse(BaseModel):
    """Verification outcome."""

    message: str
    university_verified: bool


class LoginRequest(BaseModel):
    """Authentication login credentials."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT credentials response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Token refresh input."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout revocation input."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Generic status response message."""

    message: str
