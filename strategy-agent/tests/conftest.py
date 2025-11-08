"""Pytest configuration and fixtures."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["PROJECT_ID"] = "test-project"
    os.environ["LOCATION"] = "asia-northeast1"
    os.environ["PUBSUB_TOPIC"] = "test-topic"
    os.environ["GEMINI_MODEL"] = "gemini-2.0-flash-exp"
    os.environ["USE_MOCK_GEMINI"] = "true"
    os.environ["USE_MOCK_FIRESTORE"] = "true"
    os.environ["USE_MOCK_PUBSUB"] = "true"
    os.environ["PORT"] = "8000"
    os.environ["LOG_LEVEL"] = "INFO"


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # Import here after environment is set up
    from app.main import app

    return TestClient(app)


@pytest.fixture
def mock_user_id():
    """Standard test user ID."""
    return "test_user_123"


@pytest.fixture
def sample_goal():
    """Sample marketing goal for testing."""
    return "Launch awareness campaign for new AI-powered feature"


@pytest.fixture
def sample_event_id():
    """Sample event ID for testing."""
    return "01JD4S3ABCTEST123"
