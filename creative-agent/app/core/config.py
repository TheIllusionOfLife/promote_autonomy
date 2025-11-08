"""Configuration management for Creative Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google Cloud Configuration
    PROJECT_ID: str
    LOCATION: str = "asia-northeast1"
    STORAGE_BUCKET: str

    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH: str = "./service-account-key.json"

    # Vertex AI Configuration
    IMAGEN_MODEL: str = "imagen-3.0-generate-001"
    VEO_MODEL: str = "veo-001"

    # Pub/Sub Configuration
    PUBSUB_SECRET_TOKEN: str

    # Mock Mode Flags
    USE_MOCK_IMAGEN: bool = False
    USE_MOCK_VEO: bool = False
    USE_MOCK_FIRESTORE: bool = False
    USE_MOCK_STORAGE: bool = False

    # Server Configuration
    PORT: int = 8001
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
