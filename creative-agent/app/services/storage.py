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

    async def delete_reference_image(self, event_id: str) -> None:
        """Delete reference image from mock storage.

        Args:
            event_id: Event ID whose reference image to delete
        """
        # Delete all files matching reference_image pattern
        keys_to_delete = [
            key for key in self.files.keys()
            if key.startswith(f"{event_id}/reference_image")
        ]
        for key in keys_to_delete:
            del self.files[key]


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
        """Upload file to Cloud Storage.

        SECURITY NOTE: This method makes uploaded files permanently publicly accessible.
        This is intentional for promotional marketing assets that are meant to be shared.
        All files in this bucket should be considered public content.

        Alternative: Use signed URLs with expiration for time-limited access.
        """
        # Create blob path
        blob_name = f"{event_id}/{filename}"
        blob = self.bucket.blob(blob_name)

        # Upload with content type
        blob.upload_from_string(content, content_type=content_type)

        # Make blob publicly readable
        # This requires storage.objects.setIamPolicy permission
        # Bucket must not have public access prevention enforced
        try:
            blob.make_public()
        except Exception as e:
            # Log error but don't fail - file is uploaded even if public access fails
            import logging
            logging.error(f"Failed to make blob public: {e}. File uploaded but not publicly accessible.")
            # Return the URL anyway - it may work if bucket-level permissions allow
            return blob.public_url

        # Return public URL
        return blob.public_url

    async def delete_reference_image(self, event_id: str) -> None:
        """Delete reference image from Cloud Storage.

        Args:
            event_id: Event ID whose reference image to delete
        """
        # List all blobs with reference_image prefix
        blobs = list(self.bucket.list_blobs(prefix=f"{event_id}/reference_image"))

        # Batch delete all matching blobs (more efficient than individual deletes)
        if blobs:
            self.bucket.delete_blobs(blobs)


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
