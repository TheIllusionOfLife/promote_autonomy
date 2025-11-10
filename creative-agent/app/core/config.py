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
    VEO_MODEL: str = "veo-3.0-generate-001"
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_TIMEOUT_SEC: int = 120  # Timeout for Gemini API calls (increased from 60s)
    IMAGEN_TIMEOUT_SEC: int = 90   # Timeout for Imagen API calls
    VEO_TIMEOUT_SEC: int = 360     # Timeout for Veo API calls (6 minutes for generation + polling)
    VEO_POLLING_INTERVAL_SEC: int = 15  # Interval for polling Veo operation status
    VIDEO_OUTPUT_GCS_BUCKET: str = ""  # GCS bucket for Veo video output (e.g., gs://bucket-name/veo-output)

    # Pub/Sub Configuration (deprecated - now using OIDC)
    PUBSUB_SECRET_TOKEN: str = ""  # Optional, no longer used with OIDC auth
    PUBSUB_SERVICE_ACCOUNT: str = "pubsub-invoker@promote-autonomy.iam.gserviceaccount.com"  # Expected service account for OIDC verification

    # Mock Mode Flags
    USE_MOCK_GEMINI: bool = False  # For copy.py and video.py
    USE_MOCK_IMAGEN: bool = False  # For image.py
    USE_MOCK_VEO: bool = False      # For video.py (if using Veo for actual videos)
    USE_MOCK_FIRESTORE: bool = False
    USE_MOCK_STORAGE: bool = False

    # ADK Integration Flags
    USE_ADK_ORCHESTRATION: bool = False  # Use ADK for agent orchestration (experimental)
    ADK_ROLLOUT_PERCENTAGE: int = 0  # Percentage of jobs to use ADK orchestration (0-100)

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
