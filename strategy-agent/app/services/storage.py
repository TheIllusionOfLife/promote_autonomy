"""Cloud Storage service for reference image uploads."""

from typing import Protocol
from fastapi import UploadFile

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

    async def upload_reference_image(self, event_id: str, file: UploadFile) -> str:
        """Upload reference product image.

        Args:
            event_id: Event ID for organizing files
            file: Uploaded file

        Returns:
            Public URL of uploaded image
        """
        ...

    async def delete_reference_image(self, event_id: str) -> None:
        """Delete reference image for an event.

        Args:
            event_id: Event ID whose reference image to delete
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

    async def upload_reference_image(
        self, event_id: str, content: bytes, content_type: str
    ) -> str:
        """Upload reference image to mock storage.

        Args:
            event_id: Event ID for organizing files
            content: Image file content (already read)
            content_type: MIME type (image/jpeg or image/png)

        Returns:
            Mock public URL
        """
        # Detect file extension from content type
        ext = ".png" if content_type == "image/png" else ".jpg"
        filename = f"reference_image{ext}"

        return await self.upload_file(event_id, filename, content, content_type)

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
        """
        # Create blob path
        blob_name = f"{event_id}/{filename}"
        blob = self.bucket.blob(blob_name)

        # Upload with content type
        blob.upload_from_string(content, content_type=content_type)

        # Make blob publicly readable
        try:
            blob.make_public()
        except Exception as e:
            import logging
            logging.error(f"Failed to make blob public: {e}. File uploaded but not publicly accessible.")
            return blob.public_url

        return blob.public_url

    async def upload_reference_image(
        self, event_id: str, content: bytes, content_type: str
    ) -> str:
        """Upload reference product image to Cloud Storage.

        Args:
            event_id: Event ID for organizing files
            content: Image file content (already read)
            content_type: MIME type (image/jpeg or image/png)

        Returns:
            Public URL of uploaded image
        """
        # Detect file extension from content type
        ext = ".png" if content_type == "image/png" else ".jpg"
        filename = f"reference_image{ext}"

        return await self.upload_file(event_id, filename, content, content_type)

    async def delete_reference_image(self, event_id: str) -> None:
        """Delete reference image from Cloud Storage.

        Args:
            event_id: Event ID whose reference image to delete
        """
        # List all blobs with reference_image prefix
        blobs = list(self.bucket.list_blobs(prefix=f"{event_id}/reference_image"))

        # Delete each matching blob
        for blob in blobs:
            blob.delete()


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
