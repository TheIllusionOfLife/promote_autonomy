# Promote Autonomy - Shared Schemas

Shared Pydantic models and schemas used across Strategy Agent and Creative Agent services.

## Overview

This package provides the core data models that define the contract between:
- Strategy Agent (producer of task lists)
- Creative Agent (consumer of task lists)
- Firestore (job state storage)

## Installation

From strategy-agent or creative-agent:

```bash
uv add ../shared
```

## Usage

```python
from promote_autonomy_shared import (
    TaskList,
    CaptionTaskConfig,
    ImageTaskConfig,
    Job,
    JobStatus,
)

# Create a task list
task_list = TaskList(
    goal="Launch new feature",
    captions=CaptionTaskConfig(n=3, style="twitter"),
    image=ImageTaskConfig(prompt="Modern blue visual"),
)

# Create a job
job = Job(
    event_id="01JD4S3ABC",
    uid="user123",
    status=JobStatus.PENDING_APPROVAL,
    task_list=task_list,
    created_at="2025-11-08T10:00:00Z",
    updated_at="2025-11-08T10:00:00Z",
)
```

## Models

### TaskList
Defines what assets to generate (captions, images, videos).

### Job
Firestore document model with status, task_list, and generated assets.

### JobStatus
Enum: `pending_approval`, `processing`, `completed`, `rejected`, `failed`

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check . --fix
```
