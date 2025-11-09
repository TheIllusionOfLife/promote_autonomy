"""Unit tests for Creative Agent API endpoints."""

import base64
import json
import pytest

from promote_autonomy_shared.schemas import TaskList, JobStatus, CaptionTaskConfig

from app.services.firestore import get_firestore_service


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, test_client):
        """Test health check returns 200."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "creative-agent"


class TestConsumeEndpoint:
    """Tests for Pub/Sub consume endpoint."""

    def test_consume_missing_auth_header(self, test_client):
        """Test consume endpoint requires authorization header."""
        pubsub_message = {
            "message": {"data": "eyJ0ZXN0IjogInRlc3QifQ=="},
            "subscription": "test-subscription",
        }

        response = test_client.post("/api/consume", json=pubsub_message)

        assert response.status_code == 401

    def test_consume_invalid_auth_token(self, test_client):
        """Test consume endpoint rejects invalid token."""
        pubsub_message = {
            "message": {"data": "eyJ0ZXN0IjogInRlc3QifQ=="},
            "subscription": "test-subscription",
        }

        response = test_client.post(
            "/api/consume",
            json=pubsub_message,
            headers={"Authorization": "Bearer wrong-token"},
        )

        assert response.status_code == 401

    def test_consume_invalid_message_format(self, test_client):
        """Test consume endpoint rejects malformed messages."""
        pubsub_message = {
            "message": {"data": "not-valid-base64-!@#$"},
            "subscription": "test-subscription",
        }

        response = test_client.post(
            "/api/consume",
            json=pubsub_message,
            headers={"Authorization": "Bearer test-secret-token"},
        )

        assert response.status_code == 400

    def test_consume_job_not_found(self, test_client):
        """Test consume endpoint handles missing job."""
        message_data = {
            "event_id": "nonexistent-job",
            "task_list": {"goal": "Test goal", "captions": {"n": 1, "style": "engaging"}},
        }
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

        pubsub_message = {
            "message": {"data": encoded_data},
            "subscription": "test-subscription",
        }

        response = test_client.post(
            "/api/consume",
            json=pubsub_message,
            headers={"Authorization": "Bearer test-secret-token"},
        )

        assert response.status_code == 404

    def test_consume_job_wrong_status(self, test_client):
        """Test consume endpoint rejects jobs not in processing state."""
        # Create a job in pending_approval state
        firestore_service = get_firestore_service()
        task_list = TaskList(goal="Test goal", captions=CaptionTaskConfig(n=1))
        firestore_service.jobs["test-event-id"] = {
            "event_id": "test-event-id",
            "uid": "test-user",
            "status": JobStatus.PENDING_APPROVAL,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
        }

        message_data = {
            "event_id": "test-event-id",
            "task_list": task_list.model_dump(),
        }
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

        pubsub_message = {
            "message": {"data": encoded_data},
            "subscription": "test-subscription",
        }

        response = test_client.post(
            "/api/consume",
            json=pubsub_message,
            headers={"Authorization": "Bearer test-secret-token"},
        )

        assert response.status_code == 409

    def test_consume_idempotent_completed_job(self, test_client):
        """Test consume endpoint is idempotent for completed jobs."""
        # Create a completed job
        firestore_service = get_firestore_service()
        task_list = TaskList(goal="Test goal", captions=CaptionTaskConfig(n=1))
        firestore_service.jobs["completed-job"] = {
            "event_id": "completed-job",
            "uid": "test-user",
            "status": JobStatus.COMPLETED,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
            "captions": ["https://example.com/captions.json"],
        }

        message_data = {
            "event_id": "completed-job",
            "task_list": task_list.model_dump(),
        }
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

        pubsub_message = {
            "message": {"data": encoded_data},
            "subscription": "test-subscription",
        }

        response = test_client.post(
            "/api/consume",
            json=pubsub_message,
            headers={"Authorization": "Bearer test-secret-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_completed"

    def test_consume_success_captions_only(self, test_client):
        """Test successful caption generation."""
        # Create a processing job
        firestore_service = get_firestore_service()
        task_list = TaskList(
            goal="Launch viral campaign",
            captions=CaptionTaskConfig(n=3, style="professional"),
        )
        firestore_service.jobs["caption-job"] = {
            "event_id": "caption-job",
            "uid": "test-user",
            "status": JobStatus.PROCESSING,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
        }

        message_data = {
            "event_id": "caption-job",
            "task_list": task_list.model_dump(),
        }
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

        pubsub_message = {
            "message": {"data": encoded_data},
            "subscription": "test-subscription",
        }

        response = test_client.post(
            "/api/consume",
            json=pubsub_message,
            headers={"Authorization": "Bearer test-secret-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "captions" in data["outputs"]

        # Verify job updated to completed
        updated_job = firestore_service.jobs["caption-job"]
        assert updated_job["status"] == JobStatus.COMPLETED

    def test_consume_success_all_assets(self, test_client):
        """Test successful generation of all asset types."""
        from promote_autonomy_shared.schemas import ImageTaskConfig, VideoTaskConfig

        firestore_service = get_firestore_service()
        task_list = TaskList(
            goal="Complete campaign",
            captions=CaptionTaskConfig(n=2, style="casual"),
            image=ImageTaskConfig(prompt="Product image", size="1024x1024"),
            video=VideoTaskConfig(prompt="Product video", duration_sec=30),
        )
        firestore_service.jobs["all-assets-job"] = {
            "event_id": "all-assets-job",
            "uid": "test-user",
            "status": JobStatus.PROCESSING,
            "task_list": task_list.model_dump(),
            "created_at": "2025-11-08T10:00:00Z",
            "updated_at": "2025-11-08T10:00:00Z",
        }

        message_data = {
            "event_id": "all-assets-job",
            "task_list": task_list.model_dump(),
        }
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

        pubsub_message = {
            "message": {"data": encoded_data},
            "subscription": "test-subscription",
        }

        response = test_client.post(
            "/api/consume",
            json=pubsub_message,
            headers={"Authorization": "Bearer test-secret-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "captions" in data["outputs"]
        assert "image" in data["outputs"]
        assert "video" in data["outputs"]

        # Verify all outputs are URLs
        assert data["outputs"]["captions"].startswith("https://")
        assert data["outputs"]["image"].startswith("https://")
        assert data["outputs"]["video"].startswith("https://")
