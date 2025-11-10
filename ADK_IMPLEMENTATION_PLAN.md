# ADK Integration Implementation Plan

**Project**: Promote Autonomy - Agent Orchestration with Google ADK
**Date**: November 10, 2025
**Estimated Effort**: 2-3 weeks (1 engineer)
**Approach**: Hybrid Architecture (ADK for orchestration, microservices for infrastructure)

---

## 🎯 Executive Summary

Replace current manual orchestration logic with Google's Agent Development Kit (ADK) while **preserving** the proven microservices architecture (Pub/Sub, Firestore, Cloud Run).

**What Changes**: Agent logic and orchestration patterns
**What Stays**: Service boundaries, Pub/Sub communication, HITL approval flow, authentication

---

## 📊 Current State Analysis

### Orchestration Points Identified

#### 1. **Strategy Agent** (strategy-agent/app/services/gemini.py)
- **Current**: Single Gemini API call to generate task list
- **Orchestration Complexity**: LOW (no sub-agents, single LLM call)
- **ADK Value**: Minimal (already simple)
- **Recommendation**: ⚠️ Optional - add ADK for future extensibility only

#### 2. **Creative Agent** (creative-agent/app/routers/consume.py)
- **Current**: Manual `asyncio.gather()` for parallel execution of:
  - Copy generation (Gemini 2.5 Flash)
  - Image generation (Imagen 4.0)
  - Video generation (Veo 3.0)
- **Orchestration Complexity**: MEDIUM (parallel tasks, error handling, timeout management)
- **ADK Value**: HIGH (built-in orchestration, evaluation framework, agent hierarchy)
- **Recommendation**: ✅ **Primary target for ADK integration**

### Current Service Architecture

```
┌─────────────────────────────────────────────┐
│ Strategy Service                            │
│ ├─ /strategize endpoint                     │
│ │  └─ gemini.generate_task_list()           │ ← Single LLM call
│ └─ /approve endpoint                        │
│    └─ Firestore transaction + Pub/Sub       │
└────────────────────┬────────────────────────┘
                     │ Pub/Sub Message
                     ↓
┌─────────────────────────────────────────────┐
│ Creative Service                            │
│ └─ /consume endpoint                        │
│    └─ asyncio.gather(                       │ ← Manual orchestration
│         copy_service.generate_captions(),   │
│         image_service.generate_image(),     │
│         video_service.generate_video()      │
│       )                                     │
└─────────────────────────────────────────────┘
```

---

## 🏗️ Target Architecture: ADK Hybrid

### Design Principles

1. **ADK as Library, Not Framework**: Use ADK for agent logic, not infrastructure
2. **Preserve Service Boundaries**: Keep Strategy + Creative as separate Cloud Run services
3. **Maintain Pub/Sub Communication**: Async execution critical for long-running tasks
4. **Keep HITL Approval Flow**: Firestore transactions remain unchanged
5. **Incremental Migration**: Phase-by-phase rollout with feature flags

### Target Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│ Strategy Service (Cloud Run)                           │
│ ┌────────────────────────────────────────────────────┐ │
│ │ [OPTIONAL] ADK Strategy Agent                      │ │
│ │   - LlmAgent(name="strategy_planner")              │ │
│ │   - Tools: platform_specs, gemini_generate         │ │
│ └────────────────────────────────────────────────────┘ │
│ FastAPI Endpoints:                                     │
│   POST /strategize → (optional) agent.run() or direct │
│   POST /approve → Firestore transaction → Pub/Sub     │
└───────────────────────────┬────────────────────────────┘
                            │ Pub/Sub (unchanged)
                            ↓
┌────────────────────────────────────────────────────────┐
│ Creative Service (Cloud Run)                           │
│ ┌────────────────────────────────────────────────────┐ │
│ │ ADK Multi-Agent Coordinator                        │ │
│ │                                                    │ │
│ │ creative_coordinator = LlmAgent(                  │ │
│ │   name="creative_director",                       │ │
│ │   model="gemini-2.5-flash",                       │ │
│ │   sub_agents=[                                    │ │
│ │     copy_agent,      # Captions                   │ │
│ │     image_agent,     # Imagen                     │ │
│ │     video_agent      # Veo                        │ │
│ │   ]                                               │ │
│ │ )                                                 │ │
│ └────────────────────────────────────────────────────┘ │
│ FastAPI Wrapper:                                       │
│   POST /consume → coordinator.run(task_list)           │
└────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Plan: Phase-by-Phase

### Phase 1: Setup & Dependencies (2-3 days)

#### 1.1 Add ADK to Dependencies

**Files to modify:**
- `creative-agent/pyproject.toml`
- `strategy-agent/pyproject.toml` (optional)

**Changes:**
```toml
# creative-agent/pyproject.toml
[project]
dependencies = [
    # ... existing dependencies
    "google-adk>=1.0.0",  # NEW
]
```

**Tasks:**
- [ ] Add `google-adk>=1.0.0` to creative-agent dependencies
- [ ] Run `uv sync` to install ADK
- [ ] Verify ADK imports work: `from google.adk.agents import LlmAgent`
- [ ] (Optional) Add ADK to strategy-agent dependencies

**Validation:**
```bash
# Test ADK installation
cd creative-agent
python -c "from google.adk.agents import LlmAgent; print('ADK installed successfully')"
```

#### 1.2 Create ADK Feature Flag

**Files to modify:**
- `creative-agent/app/core/config.py`
- `creative-agent/.env.example`

**Changes:**
```python
# app/core/config.py
class Settings(BaseSettings):
    # ... existing settings

    # ADK Integration
    USE_ADK_ORCHESTRATION: bool = Field(
        default=False,
        description="Use ADK for agent orchestration (experimental)"
    )
```

**Tasks:**
- [ ] Add `USE_ADK_ORCHESTRATION` setting
- [ ] Update `.env.example` with new flag
- [ ] Document flag in README.md

---

### Phase 2: Convert Services to ADK Tools (3-4 days)

#### 2.1 Create ADK-Compatible Tool Wrappers

**New files to create:**
- `creative-agent/app/agents/__init__.py`
- `creative-agent/app/agents/tools.py`
- `creative-agent/app/agents/coordinator.py`

**Implementation: `app/agents/tools.py`**

```python
"""ADK tools for asset generation."""

import asyncio
from typing import Any
from google.adk.tools import Tool
from promote_autonomy_shared.schemas import (
    CaptionTaskConfig,
    ImageTaskConfig,
    VideoTaskConfig,
)

from app.services.copy import get_copy_service
from app.services.image import get_image_service
from app.services.video import get_video_service
from app.services.storage import get_storage_service


@Tool(description="Generate social media captions using Gemini")
async def generate_captions_tool(
    config: dict[str, Any],
    goal: str,
    event_id: str
) -> dict[str, str]:
    """Generate captions and upload to Cloud Storage.

    Args:
        config: Caption configuration (n, style)
        goal: Marketing goal for context
        event_id: Job ID for storage path

    Returns:
        Dict with captions_url key
    """
    caption_config = CaptionTaskConfig(**config)
    copy_service = get_copy_service()
    storage_service = get_storage_service()

    # Generate captions
    captions = await copy_service.generate_captions(caption_config, goal)

    # Upload to storage
    import json
    captions_json = json.dumps(captions, indent=2).encode("utf-8")
    url = await storage_service.upload_file(
        event_id=event_id,
        filename="captions.json",
        content=captions_json,
        content_type="application/json",
    )

    return {"captions_url": url}


@Tool(description="Generate promotional images using Imagen")
async def generate_image_tool(
    config: dict[str, Any],
    event_id: str
) -> dict[str, str]:
    """Generate image and upload to Cloud Storage.

    Args:
        config: Image configuration (prompt, size, aspect_ratio, max_file_size_mb)
        event_id: Job ID for storage path

    Returns:
        Dict with image_url key
    """
    image_config = ImageTaskConfig(**config)
    image_service = get_image_service()
    storage_service = get_storage_service()

    # Generate image
    image_bytes = await image_service.generate_image(image_config)

    # Determine format based on compression
    if image_config.max_file_size_mb:
        filename = "image.jpg"
        content_type = "image/jpeg"
    else:
        filename = "image.png"
        content_type = "image/png"

    # Upload to storage
    url = await storage_service.upload_file(
        event_id=event_id,
        filename=filename,
        content=image_bytes,
        content_type=content_type,
    )

    return {"image_url": url}


@Tool(description="Generate promotional videos using Veo")
async def generate_video_tool(
    config: dict[str, Any],
    event_id: str
) -> dict[str, str]:
    """Generate video and upload to Cloud Storage.

    Args:
        config: Video configuration (prompt, duration_sec, aspect_ratio, max_file_size_mb)
        event_id: Job ID for storage path

    Returns:
        Dict with video_url key, optional warning if size exceeds limit
    """
    video_config = VideoTaskConfig(**config)
    video_service = get_video_service()
    storage_service = get_storage_service()

    # Generate video
    video_bytes = await video_service.generate_video(video_config)

    # Check size and create warning if needed
    warning = None
    if video_config.max_file_size_mb:
        size_mb = len(video_bytes) / (1024 * 1024)
        if size_mb > video_config.max_file_size_mb:
            warning = (
                f"Generated video size ({size_mb:.2f} MB) exceeds "
                f"platform limit ({video_config.max_file_size_mb} MB). "
                f"This video may not upload successfully to the target platform."
            )

    # Upload to storage
    url = await storage_service.upload_file(
        event_id=event_id,
        filename="video.mp4",
        content=video_bytes,
        content_type="video/mp4",
    )

    result = {"video_url": url}
    if warning:
        result["warning"] = warning

    return result
```

**Tasks:**
- [ ] Create `app/agents/` directory
- [ ] Implement `generate_captions_tool` with `@Tool` decorator
- [ ] Implement `generate_image_tool` with `@Tool` decorator
- [ ] Implement `generate_video_tool` with `@Tool` decorator
- [ ] Add type hints and comprehensive docstrings
- [ ] Handle errors gracefully (tool should return error dict, not raise)

#### 2.2 Create ADK Agent Coordinator

**Implementation: `app/agents/coordinator.py`**

```python
"""ADK Multi-Agent Coordinator for creative asset generation."""

import logging
from google.adk.agents import LlmAgent
from promote_autonomy_shared.schemas import TaskList

from app.agents.tools import (
    generate_captions_tool,
    generate_image_tool,
    generate_video_tool,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def create_copy_agent() -> LlmAgent:
    """Create ADK agent for caption generation."""
    return LlmAgent(
        name="copy_writer",
        model="gemini-2.5-flash",
        instruction="""You are a creative copywriter specialized in social media captions.
        Generate engaging, on-brand captions that match the requested style.
        Always call the generate_captions_tool to create captions.""",
        description="Generates social media captions using Gemini",
        tools=[generate_captions_tool],
    )


def create_image_agent() -> LlmAgent:
    """Create ADK agent for image generation."""
    return LlmAgent(
        name="image_creator",
        model="gemini-2.5-flash",
        instruction="""You are a visual designer specialized in promotional graphics.
        Generate images that match the requested prompt, size, and aspect ratio.
        Always call the generate_image_tool to create images.""",
        description="Generates promotional images using Imagen",
        tools=[generate_image_tool],
    )


def create_video_agent() -> LlmAgent:
    """Create ADK agent for video generation."""
    return LlmAgent(
        name="video_producer",
        model="gemini-2.5-flash",
        instruction="""You are a video producer specialized in short-form promotional videos.
        Generate videos that match the requested prompt, duration, and aspect ratio.
        Always call the generate_video_tool to create videos.""",
        description="Generates promotional videos using Veo",
        tools=[generate_video_tool],
    )


def create_creative_coordinator() -> LlmAgent:
    """Create ADK coordinator agent that orchestrates all creative agents.

    The coordinator delegates tasks to specialized sub-agents:
    - copy_writer: Generates captions
    - image_creator: Generates images
    - video_producer: Generates videos

    Returns:
        LlmAgent configured to coordinate creative asset generation
    """
    copy_agent = create_copy_agent()
    image_agent = create_image_agent()
    video_agent = create_video_agent()

    coordinator = LlmAgent(
        name="creative_director",
        model="gemini-2.5-flash",
        instruction="""You are a creative director coordinating asset generation.

        Your job is to delegate tasks to specialized agents:
        - copy_writer: For captions
        - image_creator: For images
        - video_producer: For videos

        Delegate ALL tasks in parallel for efficiency.
        Collect all results and return them in a structured format.

        If any agent fails, continue with others and report the error.""",
        description="Coordinates creative asset generation across multiple specialized agents",
        sub_agents=[copy_agent, image_agent, video_agent],
    )

    return coordinator


# Singleton instance management
_creative_coordinator: LlmAgent | None = None


def get_creative_coordinator() -> LlmAgent:
    """Get or create the creative coordinator agent (singleton).

    Returns:
        LlmAgent coordinator instance
    """
    global _creative_coordinator

    if _creative_coordinator is None:
        _creative_coordinator = create_creative_coordinator()
        logger.info("Created ADK creative coordinator agent")

    return _creative_coordinator
```

**Tasks:**
- [ ] Implement `create_copy_agent()` with appropriate instructions
- [ ] Implement `create_image_agent()` with appropriate instructions
- [ ] Implement `create_video_agent()` with appropriate instructions
- [ ] Implement `create_creative_coordinator()` with sub-agent hierarchy
- [ ] Add singleton pattern with `get_creative_coordinator()`
- [ ] Test agent creation doesn't fail on import

---

### Phase 3: Integrate ADK into Consume Endpoint (3-4 days)

#### 3.1 Create ADK Orchestration Path

**Files to modify:**
- `creative-agent/app/routers/consume.py`

**Implementation:**

```python
"""Pub/Sub consumer endpoint for Creative Agent."""

import asyncio
import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel

from promote_autonomy_shared.schemas import TaskList, JobStatus

from app.core.config import get_settings
from app.services.copy import get_copy_service
from app.services.image import get_image_service
from app.services.video import get_video_service
from app.services.firestore import get_firestore_service
from app.services.storage import get_storage_service

# NEW: ADK imports
from app.agents.coordinator import get_creative_coordinator

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


# ... existing PubSubMessage and MessageData classes ...


async def _generate_assets_with_adk(
    event_id: str,
    task_list: TaskList
) -> dict[str, str]:
    """Generate assets using ADK multi-agent orchestration.

    Args:
        event_id: Job identifier
        task_list: Task configuration

    Returns:
        Dict with keys: captions_url, image_url, video_url (as available)
    """
    logger.info(f"[ADK] Starting asset generation for job {event_id}")

    # Get ADK coordinator
    coordinator = get_creative_coordinator()

    # Prepare input for coordinator
    # ADK agents work best with structured prompts
    adk_input = {
        "event_id": event_id,
        "goal": task_list.goal,
        "target_platforms": [p.value for p in task_list.target_platforms],
        "tasks": {}
    }

    if task_list.captions:
        adk_input["tasks"]["captions"] = task_list.captions.model_dump()
    if task_list.image:
        adk_input["tasks"]["image"] = task_list.image.model_dump()
    if task_list.video:
        adk_input["tasks"]["video"] = task_list.video.model_dump()

    # Format as prompt for coordinator
    prompt = f"""Generate creative assets for this marketing campaign:

Goal: {task_list.goal}
Target Platforms: {', '.join(p.value for p in task_list.target_platforms)}
Event ID: {event_id}

Tasks to complete:
{json.dumps(adk_input['tasks'], indent=2)}

Delegate each task to the appropriate specialized agent.
Run all tasks in parallel for efficiency.
Return URLs for all generated assets."""

    try:
        # Run ADK coordinator
        # Note: ADK's run() is synchronous, so wrap in thread
        result = await asyncio.to_thread(coordinator.run, prompt)

        # Parse result (ADK returns text, need to extract URLs)
        # TODO: Improve result parsing - ADK should return structured output
        logger.info(f"[ADK] Raw result: {result}")

        # For now, extract URLs from text response
        # Better: Use ADK's structured output when available
        outputs = {}
        if "captions_url" in result:
            outputs["captions_url"] = _extract_url(result, "captions")
        if "image_url" in result:
            outputs["image_url"] = _extract_url(result, "image")
        if "video_url" in result:
            outputs["video_url"] = _extract_url(result, "video")

        logger.info(f"[ADK] Asset generation completed for job {event_id}")
        return outputs

    except Exception as e:
        logger.error(f"[ADK] Asset generation failed for job {event_id}: {e}", exc_info=True)
        raise


async def _generate_assets_legacy(
    event_id: str,
    task_list: TaskList
) -> dict[str, str]:
    """Generate assets using legacy asyncio.gather() orchestration.

    This is the current implementation, preserved for backward compatibility.
    """
    # Get services
    storage_service = get_storage_service()
    copy_service = get_copy_service()
    image_service = get_image_service()
    video_service = get_video_service()

    # Define async functions for each asset type
    async def generate_captions_task():
        if not task_list.captions:
            return None
        logger.info(f"Generating captions for job {event_id}")
        captions = await copy_service.generate_captions(task_list.captions, task_list.goal)
        captions_json = json.dumps(captions, indent=2).encode("utf-8")
        url = await storage_service.upload_file(
            event_id=event_id,
            filename="captions.json",
            content=captions_json,
            content_type="application/json",
        )
        logger.info(f"Captions generated for job {event_id}")
        return url

    async def generate_image_task():
        if not task_list.image:
            return None
        logger.info(f"Generating image for job {event_id}")
        image_bytes = await image_service.generate_image(task_list.image)
        if task_list.image.max_file_size_mb:
            filename = "image.jpg"
            content_type = "image/jpeg"
        else:
            filename = "image.png"
            content_type = "image/png"
        url = await storage_service.upload_file(
            event_id=event_id,
            filename=filename,
            content=image_bytes,
            content_type=content_type,
        )
        logger.info(f"Image generated for job {event_id}")
        return url

    async def generate_video_task():
        if not task_list.video:
            return None
        logger.info(f"Generating video for job {event_id}")
        video_bytes = await video_service.generate_video(task_list.video)

        # Check if video exceeds size limit and store warning
        if task_list.video.max_file_size_mb:
            size_mb = len(video_bytes) / (1024 * 1024)
            if size_mb > task_list.video.max_file_size_mb:
                warning_msg = (
                    f"Generated video size ({size_mb:.2f} MB) exceeds "
                    f"platform limit ({task_list.video.max_file_size_mb} MB). "
                    f"This video may not upload successfully to the target platform."
                )
                try:
                    firestore_service = get_firestore_service()
                    await firestore_service.add_job_warning(event_id, warning_msg)
                    logger.warning(f"Stored warning for job {event_id}: {warning_msg}")
                except Exception as e:
                    logger.error(f"Failed to store warning for job {event_id}: {e}")

        url = await storage_service.upload_file(
            event_id=event_id,
            filename="video.mp4",
            content=video_bytes,
            content_type="video/mp4",
        )
        logger.info(f"Video generated for job {event_id}")
        return url

    # Generate all assets in parallel
    logger.info(f"Starting parallel asset generation for job {event_id}")
    captions_url, image_url, video_url = await asyncio.gather(
        generate_captions_task(),
        generate_image_task(),
        generate_video_task(),
    )
    logger.info(f"All assets generated for job {event_id}")

    # Build outputs dict
    outputs = {}
    if captions_url:
        outputs["captions_url"] = captions_url
    if image_url:
        outputs["image_url"] = image_url
    if video_url:
        outputs["video_url"] = video_url

    return outputs


@router.post("/consume")
async def consume_task(
    pubsub_message: PubSubMessage,
    request: Request,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Consume task from Pub/Sub and generate assets.

    This endpoint is called by Pub/Sub push subscription.
    It validates the OIDC token from Pub/Sub, decodes the message,
    generates all requested assets, and updates Firestore.
    """
    # ... existing OIDC validation code (unchanged) ...

    # ... existing message decoding code (unchanged) ...

    event_id = message_data.event_id
    task_list = message_data.task_list

    # Get services
    firestore_service = get_firestore_service()

    # Verify job exists and is in processing state
    job = await firestore_service.get_job(event_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {event_id} not found")

    if job.status != JobStatus.PROCESSING:
        if job.status == JobStatus.COMPLETED:
            return {"status": "already_completed", "event_id": event_id}
        raise HTTPException(
            status_code=409,
            detail=f"Job {event_id} has invalid status: {job.status}",
        )

    try:
        # FEATURE FLAG: Choose orchestration method
        if settings.USE_ADK_ORCHESTRATION:
            logger.info(f"[ADK] Using ADK orchestration for job {event_id}")
            outputs = await _generate_assets_with_adk(event_id, task_list)
        else:
            logger.info(f"[LEGACY] Using legacy orchestration for job {event_id}")
            outputs = await _generate_assets_legacy(event_id, task_list)

        # Mark job as completed with all asset URLs
        await firestore_service.update_job_status(
            event_id=event_id,
            status=JobStatus.COMPLETED,
            captions_url=outputs.get("captions_url"),
            image_url=outputs.get("image_url"),
            video_url=outputs.get("video_url"),
        )
        logger.info(f"Job {event_id} completed successfully")

        return {"status": "success", "event_id": event_id, "outputs": outputs}

    except Exception as e:
        logger.error(
            f"Asset generation failed for job {event_id}: {e}",
            exc_info=True
        )

        # Mark job as failed
        await firestore_service.update_job_status(
            event_id=event_id,
            status=JobStatus.FAILED,
        )

        # Return 200 to acknowledge message (prevent Pub/Sub retries)
        return {
            "status": "failed",
            "event_id": event_id,
            "error": str(e)
        }
```

**Tasks:**
- [ ] Implement `_generate_assets_with_adk()` function
- [ ] Keep existing logic in `_generate_assets_legacy()` function
- [ ] Add feature flag check in main endpoint
- [ ] Route to ADK or legacy based on `USE_ADK_ORCHESTRATION`
- [ ] Test both paths work correctly
- [ ] Add comprehensive logging for both paths

#### 3.2 Handle ADK Result Parsing

ADK agents return text responses. Need to extract structured data.

**Options:**

**Option A: Parse text response** (quick but fragile)
```python
def _extract_url(text: str, asset_type: str) -> str | None:
    """Extract URL from ADK text response."""
    # Look for patterns like "captions_url: https://..."
    pattern = f"{asset_type}_url:\s*(https://[^\s]+)"
    match = re.search(pattern, text)
    return match.group(1) if match else None
```

**Option B: Use ADK structured output** (better, if available)
```python
# Configure agent to return JSON
coordinator = LlmAgent(
    ...,
    output_format="json",  # If ADK supports this
)
```

**Option C: Tools return results directly** (recommended)
- Modify tools to store results in a shared context/state
- Coordinator queries state after tool execution

**Recommendation**: Start with Option A, migrate to Option C for production.

**Tasks:**
- [ ] Implement URL extraction helper function
- [ ] Test with actual ADK responses
- [ ] Handle missing/malformed URLs gracefully
- [ ] Add validation that URLs are in Cloud Storage

---

### Phase 4: Testing & Validation (2-3 days)

#### 4.1 Unit Tests for ADK Tools

**New test file: `creative-agent/tests/unit/test_adk_tools.py`**

```python
"""Unit tests for ADK tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.tools import (
    generate_captions_tool,
    generate_image_tool,
    generate_video_tool,
)


@pytest.mark.asyncio
async def test_generate_captions_tool(mocker):
    """Test caption generation tool."""
    # Mock services
    mock_copy_service = AsyncMock()
    mock_copy_service.generate_captions.return_value = [
        "Caption 1",
        "Caption 2",
        "Caption 3"
    ]
    mocker.patch("app.agents.tools.get_copy_service", return_value=mock_copy_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/captions.json"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool
    config = {"n": 3, "style": "engaging"}
    result = await generate_captions_tool(config, "Test goal", "test_event_id")

    # Verify
    assert "captions_url" in result
    assert result["captions_url"] == "https://storage.googleapis.com/test/captions.json"
    mock_copy_service.generate_captions.assert_called_once()
    mock_storage_service.upload_file.assert_called_once()


@pytest.mark.asyncio
async def test_generate_image_tool(mocker):
    """Test image generation tool."""
    # Mock services
    mock_image_service = AsyncMock()
    mock_image_service.generate_image.return_value = b"fake_image_bytes"
    mocker.patch("app.agents.tools.get_image_service", return_value=mock_image_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/image.png"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool
    config = {"prompt": "Test image", "size": "1024x1024"}
    result = await generate_image_tool(config, "test_event_id")

    # Verify
    assert "image_url" in result
    assert result["image_url"] == "https://storage.googleapis.com/test/image.png"
    mock_image_service.generate_image.assert_called_once()


@pytest.mark.asyncio
async def test_generate_video_tool_with_size_warning(mocker):
    """Test video generation tool with file size warning."""
    # Mock services - video exceeds size limit
    mock_video_service = AsyncMock()
    # 6MB video (exceeds 4MB limit)
    mock_video_service.generate_video.return_value = b"x" * (6 * 1024 * 1024)
    mocker.patch("app.agents.tools.get_video_service", return_value=mock_video_service)

    mock_storage_service = AsyncMock()
    mock_storage_service.upload_file.return_value = "https://storage.googleapis.com/test/video.mp4"
    mocker.patch("app.agents.tools.get_storage_service", return_value=mock_storage_service)

    # Call tool with 4MB limit
    config = {"prompt": "Test video", "duration_sec": 8, "max_file_size_mb": 4.0}
    result = await generate_video_tool(config, "test_event_id")

    # Verify warning is included
    assert "video_url" in result
    assert "warning" in result
    assert "6.00 MB" in result["warning"]
    assert "4.0 MB" in result["warning"]
```

**Tasks:**
- [ ] Write unit tests for all three tools
- [ ] Test success cases
- [ ] Test error handling (service failures)
- [ ] Test file size warning logic
- [ ] Achieve >90% code coverage for tools

#### 4.2 Integration Tests for ADK Coordinator

**New test file: `creative-agent/tests/integration/test_adk_coordinator.py`**

```python
"""Integration tests for ADK coordinator."""

import pytest
from app.agents.coordinator import (
    create_copy_agent,
    create_image_agent,
    create_video_agent,
    create_creative_coordinator,
    get_creative_coordinator,
)


def test_create_copy_agent():
    """Test copy agent creation."""
    agent = create_copy_agent()

    assert agent.name == "copy_writer"
    assert agent.model == "gemini-2.5-flash"
    assert len(agent.tools) == 1
    assert agent.tools[0].__name__ == "generate_captions_tool"


def test_create_creative_coordinator():
    """Test coordinator creation with sub-agents."""
    coordinator = create_creative_coordinator()

    assert coordinator.name == "creative_director"
    assert len(coordinator.sub_agents) == 3

    # Verify sub-agents
    agent_names = {agent.name for agent in coordinator.sub_agents}
    assert agent_names == {"copy_writer", "image_creator", "video_producer"}


def test_get_creative_coordinator_singleton():
    """Test coordinator singleton pattern."""
    coordinator1 = get_creative_coordinator()
    coordinator2 = get_creative_coordinator()

    # Should return same instance
    assert coordinator1 is coordinator2
```

**Tasks:**
- [ ] Write integration tests for agent creation
- [ ] Test coordinator hierarchy
- [ ] Test singleton pattern
- [ ] (Optional) Test actual ADK execution with mocked tools

#### 4.3 End-to-End Testing

**Test scenarios:**

1. **ADK Orchestration Success**
   - Set `USE_ADK_ORCHESTRATION=true`
   - Submit job via /strategize
   - Approve via /approve
   - Verify /consume uses ADK path
   - Check all assets generated correctly

2. **Legacy Orchestration Success**
   - Set `USE_ADK_ORCHESTRATION=false`
   - Same flow as above
   - Verify /consume uses legacy path

3. **Mixed Workload**
   - Run 50% jobs with ADK, 50% with legacy
   - Verify both complete successfully
   - Compare performance metrics

4. **Error Handling**
   - Inject failures in Gemini/Imagen/Veo
   - Verify ADK handles errors gracefully
   - Verify job marked as FAILED in Firestore

**Tasks:**
- [ ] Create E2E test suite with both orchestration modes
- [ ] Test with mock services (USE_MOCK_GEMINI=true)
- [ ] Test with real services (staging environment)
- [ ] Measure performance: ADK vs legacy
- [ ] Validate Firestore state consistency

---

### Phase 5: Evaluation & Observability (2 days)

#### 5.1 Add ADK Evaluation Framework

ADK provides `adk eval` CLI for testing agent quality.

**Create eval sets: `creative-agent/eval_sets/`**

```json
// eval_sets/creative_coordinator_basic.evalset.json
{
  "name": "Creative Coordinator - Basic Scenarios",
  "test_cases": [
    {
      "input": "Generate assets for Instagram campaign about new coffee product",
      "expected_outputs": {
        "captions_url": "https://storage.googleapis.com/*",
        "image_url": "https://storage.googleapis.com/*"
      }
    },
    {
      "input": "Create Twitter campaign for tech product launch",
      "expected_outputs": {
        "captions_url": "https://storage.googleapis.com/*",
        "image_url": "https://storage.googleapis.com/*",
        "video_url": "https://storage.googleapis.com/*"
      }
    }
  ]
}
```

**Run evaluations:**
```bash
cd creative-agent
adk eval app/agents/coordinator.py eval_sets/creative_coordinator_basic.evalset.json
```

**Tasks:**
- [ ] Create eval sets for common scenarios
- [ ] Write eval sets for edge cases (missing tasks, errors)
- [ ] Run `adk eval` during CI/CD
- [ ] Track eval scores over time

#### 5.2 Enhanced Logging and Metrics

**Add structured logging for ADK:**

```python
# app/routers/consume.py
logger.info(
    f"[ADK] Asset generation started",
    extra={
        "event_id": event_id,
        "orchestration_mode": "adk",
        "task_count": len(task_list.tasks),
    }
)

# Track execution time
import time
start_time = time.time()
outputs = await _generate_assets_with_adk(event_id, task_list)
duration_sec = time.time() - start_time

logger.info(
    f"[ADK] Asset generation completed",
    extra={
        "event_id": event_id,
        "duration_sec": duration_sec,
        "outputs": list(outputs.keys()),
    }
)
```

**Tasks:**
- [ ] Add structured logging with `extra` fields
- [ ] Log execution time for ADK vs legacy
- [ ] Add custom metrics in Cloud Monitoring
- [ ] Create dashboard comparing orchestration modes

---

### Phase 6: Deployment & Rollout (2-3 days)

#### 6.1 Canary Deployment Strategy

**Gradual rollout plan:**

| Phase | Duration | ADK Traffic | Monitoring |
|-------|----------|-------------|------------|
| **Phase 1: Internal** | 1 week | 0% (dev env only) | Local testing |
| **Phase 2: Canary** | 1 week | 10% of production | Error rate, latency |
| **Phase 3: Ramp** | 1 week | 50% of production | Cost, quality |
| **Phase 4: Full** | Ongoing | 100% of production | All metrics |

**Implementation:**

```python
# app/core/config.py
class Settings(BaseSettings):
    USE_ADK_ORCHESTRATION: bool = Field(default=False)
    ADK_ROLLOUT_PERCENTAGE: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage of jobs to use ADK orchestration"
    )

# app/routers/consume.py
import random

def should_use_adk(event_id: str) -> bool:
    """Determine if this job should use ADK orchestration.

    Uses deterministic hash of event_id for consistent behavior.
    """
    if not settings.USE_ADK_ORCHESTRATION:
        return False

    # Deterministic selection based on event_id hash
    hash_val = int(hashlib.md5(event_id.encode()).hexdigest(), 16)
    return (hash_val % 100) < settings.ADK_ROLLOUT_PERCENTAGE

# In consume endpoint
if should_use_adk(event_id):
    outputs = await _generate_assets_with_adk(event_id, task_list)
else:
    outputs = await _generate_assets_legacy(event_id, task_list)
```

**Tasks:**
- [ ] Implement percentage-based rollout
- [ ] Use deterministic hash for consistent routing
- [ ] Deploy to staging with 100% ADK traffic
- [ ] Validate staging for 3 days
- [ ] Deploy to production with 10% ADK traffic
- [ ] Monitor for 1 week, then increase to 50%
- [ ] After 2 weeks of stable 50%, go to 100%

#### 6.2 Rollback Plan

**Rollback triggers:**

- Error rate >5% (compared to legacy)
- P95 latency >2x legacy
- Cost per job >1.5x legacy
- Critical bug in ADK path

**Rollback procedure:**

```bash
# Immediate rollback (0% ADK traffic)
gcloud run services update creative-agent \
  --region=us-central1 \
  --set-env-vars=USE_ADK_ORCHESTRATION=false

# OR partial rollback (reduce to 10%)
gcloud run services update creative-agent \
  --region=us-central1 \
  --set-env-vars=ADK_ROLLOUT_PERCENTAGE=10
```

**Tasks:**
- [ ] Document rollback procedure
- [ ] Create rollback runbook
- [ ] Test rollback in staging
- [ ] Set up alerting for rollback triggers

#### 6.3 Update Documentation

**Files to update:**
- `creative-agent/README.md`
- `CLAUDE.md`
- `DEPLOYMENT_CHECKLIST.md`

**Documentation topics:**
- ADK integration architecture
- Feature flag usage
- Rollout percentage configuration
- Troubleshooting ADK issues
- Performance comparison (ADK vs legacy)

**Tasks:**
- [ ] Update README with ADK section
- [ ] Document new environment variables
- [ ] Add ADK troubleshooting guide
- [ ] Update architecture diagrams

---

## 📊 Success Criteria

### Phase 1-2 (Setup + Tools)
- [ ] ADK installed in creative-agent
- [ ] All three tools implemented and unit tested
- [ ] Coordinator agent created with sub-agents
- [ ] No import errors on service startup

### Phase 3 (Integration)
- [ ] Feature flag controls orchestration path
- [ ] ADK path generates assets successfully
- [ ] Legacy path unchanged and working
- [ ] Both paths produce identical results

### Phase 4 (Testing)
- [ ] >90% code coverage for ADK code
- [ ] All unit tests passing
- [ ] E2E tests pass for both orchestration modes
- [ ] Performance benchmarks completed

### Phase 5 (Evaluation)
- [ ] ADK eval sets created
- [ ] Evaluation scores >80% (quality threshold)
- [ ] Logging and metrics in place
- [ ] Dashboard showing ADK vs legacy comparison

### Phase 6 (Deployment)
- [ ] Staging deployment with 100% ADK traffic
- [ ] Production canary at 10% for 1 week (no issues)
- [ ] Production at 50% for 1 week (no issues)
- [ ] Production at 100% (full rollout)

---

## 🚧 Risks & Mitigation

### Risk 1: ADK Performance
**Risk**: ADK coordination overhead may increase latency.

**Mitigation**:
- Benchmark early in Phase 4
- If >20% slower, optimize tool calls
- If unacceptable, keep legacy as default

### Risk 2: ADK Result Parsing
**Risk**: Extracting structured data from text responses is fragile.

**Mitigation**:
- Implement robust parsing with fallbacks
- Explore ADK structured output options
- Consider tool state management pattern

### Risk 3: ADK Framework Stability
**Risk**: ADK v1.0.0 is new, may have bugs.

**Mitigation**:
- Extensive testing in staging
- Gradual rollout with canary deployment
- Keep legacy path as rollback option
- Monitor ADK GitHub issues

### Risk 4: Increased Complexity
**Risk**: Maintaining two orchestration paths increases complexity.

**Mitigation**:
- Comprehensive unit tests for both paths
- Clear documentation
- Plan to deprecate legacy after 3 months of stable ADK

### Risk 5: Cost
**Risk**: ADK may use more Gemini tokens for coordination.

**Mitigation**:
- Track token usage per job
- Compare cost: ADK vs legacy
- Use cheaper model (gemini-2.5-flash) for coordination
- If cost >20% higher, re-evaluate

---

## 📈 Performance Benchmarks

### Metrics to Track

| Metric | Legacy (Baseline) | ADK (Target) | Status |
|--------|-------------------|--------------|--------|
| **Execution Time** | 45s avg | <60s (<33% increase) | TBD |
| **Error Rate** | 2% | <3% | TBD |
| **Cost per Job** | $0.05 | <$0.06 | TBD |
| **Token Usage** | 5K tokens | <7K tokens | TBD |
| **Code Complexity** | 250 lines | <300 lines | TBD |

### Evaluation Scenarios

1. **Simple Job** (captions only)
   - Legacy: ~10s
   - ADK: Target <15s

2. **Medium Job** (captions + image)
   - Legacy: ~30s
   - ADK: Target <40s

3. **Complex Job** (captions + image + video)
   - Legacy: ~60s (Veo is slow)
   - ADK: Target <80s

---

## 🔄 Migration Timeline

### Week 1-2: Development
- Phase 1: Setup & Dependencies
- Phase 2: Convert Services to ADK Tools

### Week 3: Integration & Testing
- Phase 3: Integrate ADK into Consume Endpoint
- Phase 4: Testing & Validation

### Week 4: Deployment
- Phase 5: Evaluation & Observability
- Phase 6: Canary Deployment (10%)

### Week 5-6: Ramp-up
- Production 50% (Week 5)
- Production 100% (Week 6)
- Monitor and optimize

### Week 7+: Maintenance
- Deprecate legacy path (if ADK stable)
- Enhance ADK agents (add brand agent, etc.)
- Integrate with future features (roadmap)

---

## 🎯 Optional Enhancements (Post-Migration)

### 1. Strategy Agent ADK Integration
**Effort**: 1-2 days
**Value**: Future extensibility for brand agent, compliance agent

```python
# strategy-agent/app/agents/strategy.py
strategy_agent = LlmAgent(
    name="strategy_planner",
    model="gemini-2.5-pro",
    tools=[
        platform_specs_tool,
        brand_guidelines_tool,  # Future
    ]
)
```

### 2. Brand Style Guide Agent (Roadmap Phase 3.3)
**Effort**: 2-3 days
**Value**: Brand consistency across campaigns

```python
brand_agent = LlmAgent(
    name="brand_guardian",
    tools=[
        retrieve_brand_colors,
        retrieve_brand_voice,
    ]
)

# Add as sub-agent to creative coordinator
coordinator = LlmAgent(
    sub_agents=[copy_agent, image_agent, video_agent, brand_agent]
)
```

### 3. ADK Development UI
**Effort**: 1 day
**Value**: Visual debugging for prompts and agent decisions

```bash
# Start ADK dev UI
adk ui --agent app.agents.coordinator:get_creative_coordinator
```

### 4. Multi-Variant Generation (A/B Testing)
**Effort**: 2-3 days
**Value**: Generate multiple caption/image variants for testing

```python
# Configure agent to generate 3 variants
coordinator = LlmAgent(
    ...,
    instruction="Generate 3 variants of each asset for A/B testing"
)
```

---

## 📚 Resources

### ADK Documentation
- Official Docs: https://google.github.io/adk-docs/
- GitHub: https://github.com/google/adk-python
- Quickstart: https://google.github.io/adk-docs/get-started/quickstart/

### Related Documents
- `CLAUDE.md` - Project architecture overview
- `FEATURE_ROADMAP.md` - Future feature plans
- `creative-agent/README.md` - Service documentation

### Monitoring & Debugging
- Cloud Run Logs: https://console.cloud.google.com/run
- ADK Dev UI: `adk ui`
- Vertex AI Monitoring: https://console.cloud.google.com/vertex-ai

---

## ✅ Next Steps

1. **Review this plan** with team for feedback
2. **Create GitHub issues** for each phase
3. **Set up project board** to track progress
4. **Start Phase 1** (Setup & Dependencies)

---

**Document Version**: 1.0
**Author**: Claude Code
**Last Updated**: November 10, 2025
**Status**: Draft - Pending Review
