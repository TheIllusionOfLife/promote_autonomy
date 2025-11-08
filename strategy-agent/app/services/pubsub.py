"""Pub/Sub service for task distribution."""

import json
import logging
from typing import Protocol

from promote_autonomy_shared.schemas import TaskList

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PubSubService(Protocol):
    """Protocol for Pub/Sub service implementations."""

    async def publish_task(self, event_id: str, task_list: TaskList) -> str:
        """Publish a task list to Pub/Sub."""
        ...


class MockPubSubService:
    """Mock Pub/Sub implementation."""

    def __init__(self):
        """Initialize mock service."""
        self.published_messages: list[dict] = []
        logger.info("[MOCK] Initialized mock Pub/Sub service")

    async def publish_task(self, event_id: str, task_list: TaskList) -> str:
        """Mock publish - stores message in memory."""
        message = {
            "event_id": event_id,
            "task_list": task_list.model_dump(mode="json"),
        }
        self.published_messages.append(message)

        logger.info(
            f"[MOCK] Published task for job {event_id} to topic "
            f"{settings.PUBSUB_TOPIC}"
        )
        return f"mock_message_id_{event_id}"


class RealPubSubService:
    """Real Pub/Sub implementation."""

    def __init__(self):
        """Initialize Pub/Sub publisher."""
        try:
            from google.cloud import pubsub_v1

            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(
                settings.PROJECT_ID,
                settings.PUBSUB_TOPIC,
            )
            logger.info(f"Initialized Pub/Sub publisher for topic {self.topic_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub: {e}")
            raise

    async def publish_task(self, event_id: str, task_list: TaskList) -> str:
        """Publish task list to Pub/Sub topic."""
        message = {
            "event_id": event_id,
            "task_list": task_list.model_dump(mode="json"),
        }

        message_data = json.dumps(message).encode("utf-8")

        # Publish message
        future = self.publisher.publish(self.topic_path, message_data)
        message_id = future.result()  # Block until published

        logger.info(
            f"Published task for job {event_id} to {self.topic_path}, "
            f"message_id: {message_id}"
        )
        return message_id


def get_pubsub_service() -> PubSubService:
    """Get Pub/Sub service (mock or real based on settings)."""
    if settings.USE_MOCK_PUBSUB:
        return MockPubSubService()
    return RealPubSubService()
