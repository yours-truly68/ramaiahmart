import json
from typing import Any

from pydantic import field_validator
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
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 60

    # University Verification
    ALLOWED_EMAIL_DOMAINS: list[str] = ["ramaiah.edu", "msrit.edu", "gmail.com"]

    @field_validator("ALLOWED_EMAIL_DOMAINS", mode="before")
    @classmethod
    def parse_allowed_domains(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [d.strip() for d in v.split(",") if d.strip()]
        return v

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
