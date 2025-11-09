"""Cloud Storage service for asset uploads."""

import datetime
from typing import Protocol

from app.core.config import get_settings



class StorageService(Protocol):
    """Protocol for storage operations."""

    async def upload_file(self, event_id: str, filename: str, content: bytes, content_type: str) -> str:
        """Upload file to storage.

        Args:
            event_id: Event ID for organizing files
            filename: Name of file
            content: File content bytes
            content_type: MIME type

        Returns:
            Public URL of uploaded file
        """
        ...


class MockStorageService:
    """Mock storage for testing."""

    def __init__(self):
        """Initialize mock storage."""
        self.files: dict[str, bytes] = {}

    async def upload_file(self, event_id: str, filename: str, content: bytes, content_type: str) -> str:
        """Store file in memory and return mock URL."""
        key = f"{event_id}/{filename}"
        self.files[key] = content
        return f"https://storage.googleapis.com/mock-bucket/{key}"


class RealStorageService:
    """Real Cloud Storage service."""

    def __init__(self):
        """Initialize Cloud Storage client."""
        from google.cloud import storage
        from google.oauth2 import service_account

        settings = get_settings()

        # Pass credentials directly to client instead of modifying environment
        # This is thread-safe and doesn't interfere with other Google Cloud clients
        if settings.FIREBASE_CREDENTIALS_PATH:
            credentials = service_account.Credentials.from_service_account_file(
                settings.FIREBASE_CREDENTIALS_PATH
            )
            self.client = storage.Client(
                project=settings.PROJECT_ID,
                credentials=credentials
            )
        else:
            # Use Application Default Credentials (ADC) for Cloud Run
            self.client = storage.Client(project=settings.PROJECT_ID)

        self.bucket = self.client.bucket(settings.STORAGE_BUCKET)

    async def upload_file(self, event_id: str, filename: str, content: bytes, content_type: str) -> str:
        """Upload file to Cloud Storage."""
        # Create blob path
        blob_name = f"{event_id}/{filename}"
        blob = self.bucket.blob(blob_name)

        # Upload with content type
        blob.upload_from_string(content, content_type=content_type)

        # Generate signed URL (1 hour expiration)
        signed_url = blob.generate_signed_url(
            expiration=datetime.timedelta(hours=1),
            method="GET",
        )

        return signed_url


# Service instance management
_mock_storage_service: MockStorageService | None = None
_real_storage_service: RealStorageService | None = None


def get_storage_service() -> StorageService:
    """Get storage service instance (singleton)."""
    global _mock_storage_service, _real_storage_service

    settings = get_settings()

    if settings.USE_MOCK_STORAGE:
        if _mock_storage_service is None:
            _mock_storage_service = MockStorageService()
        return _mock_storage_service
    else:
        if _real_storage_service is None:
            _real_storage_service = RealStorageService()
        return _real_storage_service
