"""Tests for API endpoints."""

import json

import pytest
from unittest.mock import patch
from promote_autonomy_shared.schemas import JobStatus, Platform


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
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["instagram_feed", "twitter"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["status"] == JobStatus.PENDING_APPROVAL
        assert "message" in data
        assert data["task_list"]["target_platforms"] == ["instagram_feed", "twitter"]

    def test_strategize_requires_platforms(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test that target_platforms is required."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_strategize_single_platform(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test strategy generation for single platform."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["instagram_story"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        task_list = data["task_list"]

        # Should have platform-specific configurations
        if task_list.get("image"):
            assert task_list["image"]["aspect_ratio"] == "9:16"
            assert task_list["image"]["max_file_size_mb"] == 4.0

        if task_list.get("video"):
            assert task_list["video"]["aspect_ratio"] == "9:16"
            assert task_list["video"]["duration_sec"] <= 15
            assert task_list["video"]["max_file_size_mb"] == 4.0

    def test_strategize_multiple_platforms(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test strategy generation for multiple platforms uses most restrictive constraints."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["instagram_story", "twitter", "linkedin"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        task_list = data["task_list"]

        # Most restrictive video duration (Instagram Story: 15s)
        if task_list.get("video"):
            assert task_list["video"]["duration_sec"] <= 15
            # Most restrictive file size (Instagram Story: 4MB)
            assert task_list["video"]["max_file_size_mb"] == 4.0

    def test_strategize_validates_goal_length(self, test_client, mock_user_id):
        """Test goal validation rejects too short goals."""
        response = test_client.post(
            "/api/strategize",
            data={
            },
        )
        assert response.status_code == 422  # Validation error

    def test_strategize_requires_uid(self, test_client, sample_goal, auth_headers):
        """Test that uid is required."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["twitter"])
            },
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error - missing uid

    def test_strategize_rejects_uid_mismatch(self, test_client, sample_goal):
        """Test that token uid must match request uid."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["twitter"]),
                "uid": "different_user"
            },
            headers={"Authorization": "Bearer test_user_123"},
        )
        assert response.status_code == 403

    def test_aspect_ratio_warning_story_plus_twitter(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test warning for Instagram Story (9:16) + Twitter (16:9) conflict."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["instagram_story", "twitter"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have warning about aspect ratio conflict
        assert "warnings" in data
        assert len(data["warnings"]) > 0
        warning_text = " ".join(data["warnings"]).lower()
        assert "aspect ratio" in warning_text or "9:16" in warning_text

    def test_aspect_ratio_warning_feed_plus_linkedin(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test warning for Instagram Feed (1:1) + LinkedIn (1.91:1) conflict."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["instagram_feed", "linkedin"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have warning about aspect ratio conflict
        assert "warnings" in data
        assert len(data["warnings"]) > 0
        warning_text = " ".join(data["warnings"]).lower()
        assert "aspect ratio" in warning_text or "1:1" in warning_text

    def test_aspect_ratio_warning_multiple_conflicts(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test multiple warnings for Story (9:16) + Feed (1:1) + Twitter (16:9) conflicts."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["instagram_story", "instagram_feed", "twitter"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have warnings about aspect ratio conflicts
        # All three platforms have different aspect ratios
        assert "warnings" in data
        assert len(data["warnings"]) >= 1  # At least one warning for conflicts

    def test_no_aspect_ratio_warning_compatible_platforms(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test no warning for Twitter (16:9) + LinkedIn (1.91:1) - both landscape."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["twitter", "linkedin"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have no warnings for compatible platforms
        # Twitter and LinkedIn are both landscape (16:9 and 1.91:1 are close enough)
        assert "warnings" in data
        assert not data["warnings"], f"Expected no warnings for compatible platforms, but got: {data['warnings']}"

    def test_no_aspect_ratio_warning_single_platform(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test no warning for single platform (no conflicts possible)."""
        response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["instagram_story"]),
                "uid": mock_user_id
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Should have no warnings for single platform (no conflicts possible)
        assert "warnings" in data
        assert not data["warnings"], f"Expected no warnings for a single platform, but got: {data['warnings']}"


@pytest.mark.unit
class TestApproveEndpoint:
    """Tests for /approve endpoint."""

    def test_approve_workflow(self, test_client, mock_user_id, sample_goal, auth_headers):
        """Test complete approve workflow."""
        # First create a job
        create_response = test_client.post(
            "/api/strategize",
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["twitter"]),
                "uid": mock_user_id
            },
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
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["twitter"]),
                "uid": mock_user_id
            },
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
            data={
                "goal": sample_goal,
                "target_platforms": json.dumps(["twitter"]),
                "uid": mock_user_id
            },
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


@pytest.mark.unit
class TestGeminiFallback:
    """Tests for Gemini service fallback behavior."""

    @pytest.mark.asyncio
    async def test_gemini_fallback_includes_target_platforms(self):
        """Test that Gemini fallback TaskList includes required target_platforms field.

        This test verifies the fix for the critical bug where the fallback TaskList
        was missing the target_platforms field, causing ValidationError on API failure.

        Regression test for: https://github.com/TheIllusionOfLife/promote_autonomy/pull/10
        """
        from app.services.gemini import RealGeminiService

        service = RealGeminiService()

        # Mock the Gemini generate_content_async to raise an exception
        with patch.object(service.model, 'generate_content_async', side_effect=Exception("Simulated API failure")):
            platforms = [Platform.TWITTER, Platform.INSTAGRAM_FEED]
            result = await service.generate_task_list(
                goal="Test campaign for fallback validation",
                target_platforms=platforms
            )

            # CRITICAL: Fallback must include target_platforms
            assert result.target_platforms == platforms

            # Fallback should have basic captions
            assert result.captions is not None
            assert result.captions.n == 3
            assert result.captions.style == "engaging"
