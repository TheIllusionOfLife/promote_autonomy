"""Firestore service for job status updates."""

from typing import Protocol

from promote_autonomy_shared.schemas import Job, JobStatus

from app.core.config import get_settings



class FirestoreService(Protocol):
    """Protocol for Firestore operations."""

    async def get_job(self, event_id: str) -> Job | None:
        """Get job by event ID."""
        ...

    async def update_job_status(
        self,
        event_id: str,
        status: JobStatus,
        captions_url: str | None = None,
        image_url: str | None = None,
        video_url: str | None = None,
    ) -> Job:
        """Update job status and asset URLs."""
        ...


class MockFirestoreService:
    """Mock Firestore for testing."""

    def __init__(self):
        """Initialize mock database."""
        self.jobs: dict[str, dict] = {}

    async def get_job(self, event_id: str) -> Job | None:
        """Get job from mock database."""
        if event_id not in self.jobs:
            return None
        return Job(**self.jobs[event_id])

    async def update_job_status(
        self,
        event_id: str,
        status: JobStatus,
        captions_url: str | None = None,
        image_url: str | None = None,
        video_url: str | None = None,
    ) -> Job:
        """Update job in mock database."""
        from datetime import datetime, timezone

        if event_id not in self.jobs:
            raise ValueError(f"Job {event_id} not found")

        job_data = self.jobs[event_id]
        job_data["status"] = status
        job_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Update asset URLs if provided
        if captions_url:
            job_data.setdefault("captions", []).append(captions_url)
        if image_url:
            job_data.setdefault("images", []).append(image_url)
        if video_url:
            job_data.setdefault("videos", []).append(video_url)

        return Job(**job_data)


class RealFirestoreService:
    """Real Firestore service."""

    def __init__(self):
        """Initialize Firestore client."""
        from google.cloud import firestore
        import os

        settings = get_settings()

        # Set credentials path if specified
        if settings.FIREBASE_CREDENTIALS_PATH:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.FIREBASE_CREDENTIALS_PATH

        self.db = firestore.Client(project=settings.PROJECT_ID)

    async def get_job(self, event_id: str) -> Job | None:
        """Get job from Firestore."""
        doc_ref = self.db.collection("jobs").document(event_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        return Job(**doc.to_dict())

    async def update_job_status(
        self,
        event_id: str,
        status: JobStatus,
        captions_url: str | None = None,
        image_url: str | None = None,
        video_url: str | None = None,
    ) -> Job:
        """Update job status in Firestore."""
        from datetime import datetime, timezone
        from google.cloud.firestore import ArrayUnion

        doc_ref = self.db.collection("jobs").document(event_id)

        # Build update data
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Update asset URLs if provided (append to arrays)
        if captions_url:
            update_data["captions"] = ArrayUnion([captions_url])
        if image_url:
            update_data["images"] = ArrayUnion([image_url])
        if video_url:
            update_data["videos"] = ArrayUnion([video_url])

        doc_ref.update(update_data)

        # Return updated job
        updated_doc = doc_ref.get()
        return Job(**updated_doc.to_dict())


# Service instance management
_mock_firestore_service: MockFirestoreService | None = None
_real_firestore_service: RealFirestoreService | None = None


def get_firestore_service() -> FirestoreService:
    """Get Firestore service instance (singleton)."""
    global _mock_firestore_service, _real_firestore_service

    settings = get_settings()

    if settings.USE_MOCK_FIRESTORE:
        if _mock_firestore_service is None:
            _mock_firestore_service = MockFirestoreService()
        return _mock_firestore_service
    else:
        if _real_firestore_service is None:
            _real_firestore_service = RealFirestoreService()
        return _real_firestore_service
