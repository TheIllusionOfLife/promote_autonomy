"""Tests for API endpoints."""

import pytest
from promote_autonomy_shared.schemas import JobStatus


@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, test_client):
        """Test health check returns correct status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "strategy-agent"
        assert "mock_mode" in data

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns service information."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Promote Autonomy - Strategy Agent"
        assert "endpoints" in data


@pytest.mark.unit
class TestStrategizeEndpoint:
    """Tests for /strategize endpoint."""

    def test_strategize_success(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test successful strategy generation."""
        response = test_client.post(
            "/api/strategize",
            json={"goal": sample_goal, "uid": mock_user_id},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["status"] == JobStatus.PENDING_APPROVAL
        assert "message" in data

    def test_strategize_validates_goal_length(self, test_client, mock_user_id):
        """Test goal validation rejects too short goals."""
        response = test_client.post(
            "/api/strategize",
            json={"goal": "short", "uid": mock_user_id},
        )
        assert response.status_code == 422  # Validation error

    def test_strategize_validates_goal_max_length(self, test_client, mock_user_id):
        """Test goal validation rejects too long goals."""
        long_goal = "a" * 501
        response = test_client.post(
            "/api/strategize",
            json={"goal": long_goal, "uid": mock_user_id},
        )
        assert response.status_code == 422  # Validation error

    def test_strategize_requires_uid(self, test_client, sample_goal, auth_headers):
        """Test that uid is required."""
        response = test_client.post(
            "/api/strategize",
            json={"goal": sample_goal},
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_strategize_requires_auth(self, test_client, mock_user_id, sample_goal):
        """Test that authorization header is required."""
        response = test_client.post(
            "/api/strategize",
            json={"goal": sample_goal, "uid": mock_user_id},
        )
        assert response.status_code == 401

    def test_strategize_rejects_uid_mismatch(self, test_client, sample_goal):
        """Test that token uid must match request uid."""
        response = test_client.post(
            "/api/strategize",
            json={"goal": sample_goal, "uid": "different_user"},
            headers={"Authorization": "Bearer test_user_123"},
        )
        assert response.status_code == 403


@pytest.mark.unit
class TestApproveEndpoint:
    """Tests for /approve endpoint."""

    def test_approve_workflow(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test complete approve workflow."""
        # First create a job
        create_response = test_client.post(
            "/api/strategize",
            json={"goal": sample_goal, "uid": mock_user_id},
            headers=auth_headers,
        )
        assert create_response.status_code == 200
        event_id = create_response.json()["event_id"]

        # Then approve it with authorization header
        approve_response = test_client.post(
            "/api/approve",
            json={"event_id": event_id, "uid": mock_user_id},
            headers=auth_headers,
        )
        assert approve_response.status_code == 200
        data = approve_response.json()
        assert data["event_id"] == event_id
        assert data["status"] == JobStatus.PROCESSING
        assert data["published"] is True

    def test_approve_nonexistent_job(self, test_client, mock_user_id, auth_headers):
        """Test approving non-existent job returns 404."""
        response = test_client.post(
            "/api/approve",
            json={"event_id": "nonexistent_id", "uid": mock_user_id},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_approve_already_approved_job(
        self, test_client, mock_user_id, sample_goal, auth_headers
    ):
        """Test approving already approved job returns 409."""
        # Create and approve a job
        create_response = test_client.post(
            "/api/strategize",
            json={"goal": sample_goal, "uid": mock_user_id},
            headers=auth_headers,
        )
        event_id = create_response.json()["event_id"]

        test_client.post(
            "/api/approve",
            json={"event_id": event_id, "uid": mock_user_id},
            headers=auth_headers,
        )

        # Try to approve again
        second_approve = test_client.post(
            "/api/approve",
            json={"event_id": event_id, "uid": mock_user_id},
            headers=auth_headers,
        )
        assert second_approve.status_code == 409

    def test_approve_wrong_user(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test approving job by different user returns 403."""
        # Create job with one user
        create_response = test_client.post(
            "/api/strategize",
            json={"goal": sample_goal, "uid": mock_user_id},
            headers=auth_headers,
        )
        event_id = create_response.json()["event_id"]

        # Try to approve with different user
        # Use different user in request but original user's token - should trigger UID mismatch
        approve_response = test_client.post(
            "/api/approve",
            json={"event_id": event_id, "uid": "different_user"},
            headers=auth_headers,  # Still using mock_user_id token
        )
        assert approve_response.status_code == 403

    def test_approve_requires_event_id(self, test_client, mock_user_id):
        """Test that event_id is required."""
        response = test_client.post(
            "/api/approve",
            json={"uid": mock_user_id},
        )
        assert response.status_code == 422  # Validation error

    def test_approve_requires_uid(self, test_client, sample_event_id):
        """Test that uid is required."""
        response = test_client.post(
            "/api/approve",
            json={"event_id": sample_event_id},
        )
        assert response.status_code == 422  # Validation error
