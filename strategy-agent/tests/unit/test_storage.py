"""Tests for Cloud Storage service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO

from app.services.storage import (
    MockStorageService,
    RealStorageService,
    get_storage_service,
)


class TestMockStorageService:
    """Tests for MockStorageService."""

    @pytest.mark.asyncio
    async def test_upload_reference_image(self):
        """Test uploading reference image."""
        service = MockStorageService()

        # Upload with content and content_type
        content = b"fake image data"
        content_type = "image/jpeg"

        url = await service.upload_reference_image("event123", content, content_type)

        assert url.startswith("https://storage.googleapis.com/mock-bucket/event123/reference_image")
        assert url.endswith(".jpg")
        assert "event123/reference_image.jpg" in service.files

    @pytest.mark.asyncio
    async def test_upload_reference_image_png(self):
        """Test uploading reference image as PNG."""
        service = MockStorageService()

        content = b"fake png data"
        content_type = "image/png"

        url = await service.upload_reference_image("event456", content, content_type)

        assert url.endswith(".png")
        assert "event456/reference_image.png" in service.files

    @pytest.mark.asyncio
    async def test_delete_reference_image_exists(self):
        """Test deleting reference image that exists."""
        service = MockStorageService()

        # Upload first
        content = b"fake data"
        content_type = "image/jpeg"
        await service.upload_reference_image("event789", content, content_type)

        # Verify it exists
        assert "event789/reference_image.jpg" in service.files

        # Delete
        await service.delete_reference_image("event789")

        # Verify deleted
        assert "event789/reference_image.jpg" not in service.files

    @pytest.mark.asyncio
    async def test_delete_reference_image_not_exists(self):
        """Test deleting reference image that doesn't exist (should not raise)."""
        service = MockStorageService()

        # Should not raise exception
        await service.delete_reference_image("nonexistent_event")

    @pytest.mark.asyncio
    async def test_upload_file_general(self):
        """Test general file upload method."""
        service = MockStorageService()

        url = await service.upload_file(
            "event999",
            "test.txt",
            b"test content",
            "text/plain"
        )

        assert url == "https://storage.googleapis.com/mock-bucket/event999/test.txt"
        assert service.files["event999/test.txt"] == b"test content"


class TestRealStorageService:
    """Tests for RealStorageService."""

    @pytest.mark.asyncio
    async def test_upload_reference_image(self):
        """Test uploading reference image to real storage."""
        with patch("google.cloud.storage.Client") as mock_client_class:
            # Setup mocks
            mock_client = Mock()
            mock_bucket = Mock()
            mock_blob = Mock()
            mock_blob.public_url = "https://storage.googleapis.com/real-bucket/event123/reference_image.jpg"

            mock_bucket.blob.return_value = mock_blob
            mock_client.bucket.return_value = mock_bucket
            mock_client_class.return_value = mock_client

            service = RealStorageService()

            # Upload with content and content_type
            content = b"real image data"
            content_type = "image/jpeg"

            url = await service.upload_reference_image("event123", content, content_type)

            # Verify blob path
            mock_bucket.blob.assert_called_once_with("event123/reference_image.jpg")

            # Verify upload called
            mock_blob.upload_from_string.assert_called_once_with(
                b"real image data",
                content_type="image/jpeg"
            )

            # Verify make public called
            mock_blob.make_public.assert_called_once()

            # Verify URL returned
            assert url == "https://storage.googleapis.com/real-bucket/event123/reference_image.jpg"

    @pytest.mark.asyncio
    async def test_delete_reference_image(self):
        """Test deleting reference image from real storage."""
        with patch("google.cloud.storage.Client") as mock_client_class:
            # Setup mocks
            mock_client = Mock()
            mock_bucket = Mock()
            mock_blob_jpg = Mock()
            mock_blob_png = Mock()

            # Mock list_blobs to return one matching blob
            mock_bucket.list_blobs.return_value = [mock_blob_jpg]

            mock_client.bucket.return_value = mock_bucket
            mock_client_class.return_value = mock_client

            service = RealStorageService()

            await service.delete_reference_image("event123")

            # Verify list_blobs called with prefix
            mock_bucket.list_blobs.assert_called_once_with(prefix="event123/reference_image")

            # Verify batch delete called with the blob list
            mock_bucket.delete_blobs.assert_called_once_with([mock_blob_jpg])

    @pytest.mark.asyncio
    async def test_delete_reference_image_not_found(self):
        """Test deleting reference image that doesn't exist."""
        with patch("google.cloud.storage.Client") as mock_client_class:
            # Setup mocks
            mock_client = Mock()
            mock_bucket = Mock()

            # Mock list_blobs to return empty list
            mock_bucket.list_blobs.return_value = []

            mock_client.bucket.return_value = mock_bucket
            mock_client_class.return_value = mock_client

            service = RealStorageService()

            # Should not raise exception
            await service.delete_reference_image("event123")

            # Verify list_blobs called
            mock_bucket.list_blobs.assert_called_once_with(prefix="event123/reference_image")

    @pytest.mark.asyncio
    async def test_upload_reference_image_content_type_detection(self):
        """Test content type detection for different image formats."""
        with patch("google.cloud.storage.Client") as mock_client_class:
            # Setup mocks
            mock_client = Mock()
            mock_bucket = Mock()
            mock_blob = Mock()
            mock_blob.public_url = "https://storage.googleapis.com/real-bucket/event123/reference_image.png"

            mock_bucket.blob.return_value = mock_blob
            mock_client.bucket.return_value = mock_bucket
            mock_client_class.return_value = mock_client

            service = RealStorageService()

            # Test PNG
            content = b"png data"
            content_type = "image/png"

            url = await service.upload_reference_image("event123", content, content_type)

            # Verify correct extension
            mock_bucket.blob.assert_called_with("event123/reference_image.png")


def test_get_storage_service_mock():
    """Test getting mock storage service."""
    with patch("app.services.storage.get_settings") as mock_settings:
        settings = Mock()
        settings.USE_MOCK_STORAGE = True
        mock_settings.return_value = settings

        service = get_storage_service()

        assert isinstance(service, MockStorageService)


def test_get_storage_service_real():
    """Test getting real storage service."""
    with patch("app.services.storage.get_settings") as mock_settings, \
         patch("google.cloud.storage.Client"):
        settings = Mock()
        settings.USE_MOCK_STORAGE = False
        settings.PROJECT_ID = "test-project"
        settings.STORAGE_BUCKET = "test-bucket"
        settings.FIREBASE_CREDENTIALS_PATH = None
        mock_settings.return_value = settings

        service = get_storage_service()

        assert isinstance(service, RealStorageService)


def test_get_storage_service_singleton():
    """Test that get_storage_service returns same instance."""
    with patch("app.services.storage.get_settings") as mock_settings:
        settings = Mock()
        settings.USE_MOCK_STORAGE = True
        mock_settings.return_value = settings

        service1 = get_storage_service()
        service2 = get_storage_service()

        assert service1 is service2
