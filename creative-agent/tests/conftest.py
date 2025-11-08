"""Test configuration and fixtures."""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables before importing app."""
    os.environ["PROJECT_ID"] = "test-project"
    os.environ["LOCATION"] = "asia-northeast1"
    os.environ["STORAGE_BUCKET"] = "test-bucket"
    os.environ["PUBSUB_SECRET_TOKEN"] = "test-secret-token"
    os.environ["USE_MOCK_GEMINI"] = "true"
    os.environ["USE_MOCK_IMAGEN"] = "true"
    os.environ["USE_MOCK_VEO"] = "true"
    os.environ["USE_MOCK_FIRESTORE"] = "true"
    os.environ["USE_MOCK_STORAGE"] = "true"


@pytest.fixture
def test_client():
    """Create test client for FastAPI app."""
    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset service singletons between tests."""
    # Import services after environment is set up
    from app.services import firestore, storage, copy, image, video

    # Reset all singleton instances
    firestore._mock_firestore_service = None
    firestore._real_firestore_service = None

    storage._mock_storage_service = None
    storage._real_storage_service = None

    copy._mock_copy_service = None
    copy._real_copy_service = None

    image._mock_image_service = None
    image._real_image_service = None

    video._mock_video_service = None
    video._real_video_service = None

    yield
