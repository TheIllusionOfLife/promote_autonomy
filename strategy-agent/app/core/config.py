"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google Cloud Configuration
    PROJECT_ID: str
    LOCATION: str = "asia-northeast1"

    # Pub/Sub Configuration
    PUBSUB_TOPIC: str

    # Vertex AI Configuration
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_TIMEOUT_SEC: int = 60  # Timeout for Gemini API calls

    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH: str = ""

    # Mock Mode Flags (for rapid development)
    USE_MOCK_GEMINI: bool = False
    USE_MOCK_FIRESTORE: bool = False
    USE_MOCK_PUBSUB: bool = False

    # Retry Configuration
    PUBSUB_RETRY_ATTEMPTS: int = 3
    PUBSUB_RETRY_MAX_WAIT_SEC: int = 10

    # Server Configuration
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore
