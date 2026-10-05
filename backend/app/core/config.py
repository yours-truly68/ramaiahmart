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


settings = Settings()
