import json
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings resolved from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "RamaiahMart API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ramaiahmart"
    API_V1_PREFIX: str = "/api/v1"

    # Security & Tokens
    JWT_SECRET_KEY: str = "dev-insecure-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # University Email Restriction (V1: only @msrit.edu accounts are accepted)
    ALLOWED_EMAIL_DOMAINS: list[str] = ["msrit.edu"]

    # Object Storage (MinIO locally / AWS S3 in production)
    S3_ENDPOINT_URL: str | None = None
    S3_PUBLIC_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "ramaiahmart-media"
    STORAGE_PRESIGNED_EXPIRATION_SECONDS: int = 900
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_MIME_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # Database Connection Pooling (Production RDS / Local Postgres)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # CORS Origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Trusted Reverse Proxies (CIDR or IPs)
    TRUSTED_PROXIES: list[str] = [
        "127.0.0.1",
        "::1",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]

    # AI Review & Moderation (Text: Automatic on post publish, Vision: Reactive on report)
    AI_TEXT_PROVIDER: str = "mock"  # "mock", "openai", "groq"
    AI_TEXT_MODEL: str = "mock_rule_engine_v1"
    AI_TEXT_API_KEY: str | None = None
    AI_TEXT_BASE_URL: str | None = None
    AI_VISION_PROVIDER: str = "mock"  # "mock", "openai"
    AI_VISION_MODEL: str = "mock_vision_v1"
    AI_VISION_API_KEY: str | None = None
    AI_VISION_BASE_URL: str | None = None
    AI_PROVIDER_API_KEY: str | None = None
    AI_PROVIDER_BASE_URL: str | None = None
    AI_REQUEST_TIMEOUT_SECONDS: float = 10.0
    AI_MAX_RETRIES: int = 1

    # Report Abuse Protection & Rate Limiting
    REPORTS_RATE_LIMIT_PER_USER_WINDOW: int = 10
    REPORTS_RATE_LIMIT_WINDOW_SECONDS: int = 3600

    @field_validator(
        "ALLOWED_EMAIL_DOMAINS",
        "ALLOWED_IMAGE_MIME_TYPES",
        "CORS_ORIGINS",
        "TRUSTED_PROXIES",
        mode="before",
    )
    @classmethod
    def parse_string_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [d.strip() for d in v.split(",") if d.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Fail fast if insecure fallback secrets or development configs are used in production."""
        if self.APP_ENV == "production":
            dev_default = "dev-insecure-secret-key-change-in-production-min-32-chars"
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == dev_default:
                raise ValueError(
                    "Production configuration requires a dedicated, secure JWT_SECRET_KEY. "
                    "Cannot use the default development secret."
                )
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production.")
            if self.DEBUG:
                raise ValueError("DEBUG mode must be set to False in production.")

            # Database check
            if "localhost" in self.DATABASE_URL or "postgres:postgres" in self.DATABASE_URL:
                raise ValueError(
                    "Production configuration requires an explicit, production DATABASE_URL. "
                    "Cannot use default development postgres credentials or localhost."
                )

            # S3 / Object Storage check: reject dev credentials if explicitly supplied
            if self.AWS_ACCESS_KEY_ID == "minioadmin" or self.AWS_SECRET_ACCESS_KEY == "minioadmin":
                raise ValueError(
                    "Production configuration requires dedicated S3 credentials or EC2 IAM role. "
                    "Cannot use default development minioadmin credentials."
                )

            # CORS check
            if any(origin == "*" for origin in self.CORS_ORIGINS):
                raise ValueError(
                    "Wildcard '*' CORS origins are not permitted in production with credentials."
                )

            # AI Provider checks
            if self.AI_TEXT_PROVIDER != "mock":
                text_key = self.AI_TEXT_API_KEY or self.AI_PROVIDER_API_KEY
                if not text_key:
                    raise ValueError(
                        "AI_TEXT_API_KEY (or AI_PROVIDER_API_KEY) must be configured in "
                        "production when external AI text provider is enabled."
                    )
            if self.AI_VISION_PROVIDER != "mock":
                vision_key = self.AI_VISION_API_KEY or self.AI_PROVIDER_API_KEY
                if not vision_key:
                    raise ValueError(
                        "AI_VISION_API_KEY (or AI_PROVIDER_API_KEY) must be configured in "
                        "production when external AI vision provider is enabled."
                    )
        return self

    def is_university_email(self, email: str) -> bool:
        """Check if email matches configured university domains."""
        if "@" not in email:
            return False
        domain = email.split("@")[-1].lower().strip()
        return any(
            domain == allowed.lower() or domain.endswith(f".{allowed.lower()}")
            for allowed in self.ALLOWED_EMAIL_DOMAINS
        )


settings = Settings()
