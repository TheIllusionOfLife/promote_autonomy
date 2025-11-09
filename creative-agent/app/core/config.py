"""Configuration management for Creative Agent."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google Cloud Configuration
    PROJECT_ID: str
    LOCATION: str = "asia-northeast1"
    STORAGE_BUCKET: str

    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH: str = ""  # Empty = use ADC (Cloud Run default)

    # Vertex AI Configuration
    IMAGEN_MODEL: str = "imagen-3.0-generate-001"
    VEO_MODEL: str = "veo-001"
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"

    # Pub/Sub Configuration
    PUBSUB_SECRET_TOKEN: str

    # Mock Mode Flags
    USE_MOCK_GEMINI: bool = False
    USE_MOCK_IMAGEN: bool = False
    USE_MOCK_VEO: bool = False
    USE_MOCK_FIRESTORE: bool = False
    USE_MOCK_STORAGE: bool = False

    # Server Configuration
    PORT: int = 8001
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
