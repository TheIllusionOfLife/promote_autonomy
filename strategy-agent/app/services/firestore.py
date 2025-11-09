"""Firestore service for job state management."""

import logging
from datetime import datetime, timezone
from typing import Protocol

from promote_autonomy_shared.schemas import Job, JobStatus, TaskList

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FirestoreService(Protocol):
    """Protocol for Firestore service implementations."""

    async def create_job(self, event_id: str, uid: str, task_list: TaskList) -> Job:
        """Create a new job in pending_approval status."""
        ...

    async def get_job(self, event_id: str) -> Job | None:
        """Retrieve a job by event_id."""
        ...

    async def approve_job(self, event_id: str, uid: str) -> Job:
        """Atomically transition job from pending_approval to processing."""
        ...

    async def revert_to_pending(self, event_id: str) -> None:
        """Revert a job from processing back to pending_approval (rollback)."""
        ...


class MockFirestoreService:
    """Mock Firestore implementation using in-memory storage."""

    def __init__(self):
        """Initialize in-memory job storage."""
        self.jobs: dict[str, Job] = {}
        logger.info("[MOCK] Initialized mock Firestore service")

    async def create_job(self, event_id: str, uid: str, task_list: TaskList) -> Job:
        """Create a new job in memory."""
        now = datetime.now(timezone.utc).isoformat()
        job = Job(
            event_id=event_id,
            uid=uid,
            status=JobStatus.PENDING_APPROVAL,
            task_list=task_list,
            created_at=now,
            updated_at=now,
        )
        self.jobs[event_id] = job
        logger.info(f"[MOCK] Created job {event_id} with status pending_approval")
        return job

    async def get_job(self, event_id: str) -> Job | None:
        """Retrieve a job from memory."""
        job = self.jobs.get(event_id)
        if job:
            logger.info(f"[MOCK] Retrieved job {event_id}")
        else:
            logger.warning(f"[MOCK] Job {event_id} not found")
        return job

    async def approve_job(self, event_id: str, uid: str) -> Job:
        """Approve a job (transition to processing)."""
        job = self.jobs.get(event_id)
        if not job:
            raise ValueError(f"Job {event_id} not found")

        if job.uid != uid:
            raise PermissionError(
                f"User {uid} does not own job {event_id} (owner: {job.uid})"
            )

        if job.status != JobStatus.PENDING_APPROVAL:
            raise ValueError(
                f"Job {event_id} is in status {job.status}, "
                "expected pending_approval"
            )

        # Atomic transition
        now = datetime.now(timezone.utc).isoformat()
        job.status = JobStatus.PROCESSING
        job.approved_at = now
        job.updated_at = now

        logger.info(f"[MOCK] Approved job {event_id}, status -> processing")
        return job

    async def revert_to_pending(self, event_id: str) -> None:
        """Revert a job from processing back to pending_approval."""
        job = self.jobs.get(event_id)
        if not job:
            raise ValueError(f"Job {event_id} not found")

        if job.status != JobStatus.PROCESSING:
            logger.warning(
                f"[MOCK] Job {event_id} is not in processing status, "
                f"cannot revert (current: {job.status})"
            )
            return

        # Revert status
        now = datetime.now(timezone.utc).isoformat()
        job.status = JobStatus.PENDING_APPROVAL
        job.approved_at = None
        job.updated_at = now

        logger.info(f"[MOCK] Reverted job {event_id} to pending_approval")



class RealFirestoreService:
    """Real Firestore implementation."""

    def __init__(self):
        """Initialize Firestore client."""
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            # Initialize Firebase Admin SDK
            if settings.FIREBASE_CREDENTIALS_PATH:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            else:
                # Use Application Default Credentials (works in Cloud Run)
                cred = credentials.ApplicationDefault()

            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {"projectId": settings.PROJECT_ID})

            self.db = firestore.client()
            logger.info("Initialized Firestore client")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            raise

    async def create_job(self, event_id: str, uid: str, task_list: TaskList) -> Job:
        """Create a new job in Firestore."""
        now = datetime.now(timezone.utc).isoformat()
        job = Job(
            event_id=event_id,
            uid=uid,
            status=JobStatus.PENDING_APPROVAL,
            task_list=task_list,
            created_at=now,
            updated_at=now,
        )

        doc_ref = self.db.collection("jobs").document(event_id)
        doc_ref.set(job.model_dump(mode="json"))

        logger.info(f"Created job {event_id} in Firestore")
        return job

    async def get_job(self, event_id: str) -> Job | None:
        """Retrieve a job from Firestore."""
        doc_ref = self.db.collection("jobs").document(event_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.warning(f"Job {event_id} not found in Firestore")
            return None

        job = Job(**doc.to_dict())
        logger.info(f"Retrieved job {event_id} from Firestore")
        return job

    async def approve_job(self, event_id: str, uid: str) -> Job:
        """Approve a job using a Firestore transaction."""
        from google.cloud.firestore import transactional

        @transactional
        def _approve_transaction(transaction, doc_ref):
            """Atomic approval transaction."""
            snapshot = doc_ref.get(transaction=transaction)

            if not snapshot.exists:
                raise ValueError(f"Job {event_id} not found")

            job_data = snapshot.to_dict()
            job = Job(**job_data)

            # Validate ownership
            if job.uid != uid:
                raise PermissionError(
                    f"User {uid} does not own job {event_id} (owner: {job.uid})"
                )

            # Validate status
            if job.status != JobStatus.PENDING_APPROVAL:
                raise ValueError(
                    f"Job {event_id} is in status {job.status}, "
                    "expected pending_approval"
                )

            # Update job
            now = datetime.now(timezone.utc).isoformat()
            job.status = JobStatus.PROCESSING
            job.approved_at = now
            job.updated_at = now

            # Write transaction
            transaction.update(doc_ref, job.model_dump(mode="json"))

            return job

        doc_ref = self.db.collection("jobs").document(event_id)
        transaction = self.db.transaction()
        job = _approve_transaction(transaction, doc_ref)

        logger.info(f"Approved job {event_id} in Firestore transaction")
        return job

    async def revert_to_pending(self, event_id: str) -> None:
        """Revert a job from processing back to pending_approval."""
        doc_ref = self.db.collection("jobs").document(event_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise ValueError(f"Job {event_id} not found")

        job = Job(**doc.to_dict())

        if job.status != JobStatus.PROCESSING:
            logger.warning(
                f"Job {event_id} is not in processing status, "
                f"cannot revert (current: {job.status})"
            )
            return

        # Revert to pending_approval
        now = datetime.now(timezone.utc).isoformat()
        doc_ref.update({
            "status": JobStatus.PENDING_APPROVAL,
            "approved_at": None,
            "updated_at": now,
        })

        logger.info(f"Reverted job {event_id} to pending_approval in Firestore")


# Singleton instances
_mock_firestore_service: MockFirestoreService | None = None
_real_firestore_service: RealFirestoreService | None = None


def get_firestore_service() -> FirestoreService:
    """Get Firestore service (mock or real based on settings)."""
    global _mock_firestore_service, _real_firestore_service

    if settings.USE_MOCK_FIRESTORE:
        if _mock_firestore_service is None:
            _mock_firestore_service = MockFirestoreService()
        return _mock_firestore_service
    else:
        if _real_firestore_service is None:
            _real_firestore_service = RealFirestoreService()
        return _real_firestore_service
