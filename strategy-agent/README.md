# Strategy Agent

AI-powered marketing strategy generation with Human-in-the-Loop approval.

## Overview

The Strategy Agent generates marketing task lists using Gemini AI and manages the approval workflow before asset generation begins.

## Endpoints

### POST /api/strategize

Generate marketing strategy from goal with optional product image.

**Content-Type**: `multipart/form-data`

**Form Fields**:
- `goal` (required): Marketing goal (10-500 characters)
- `target_platforms` (required): JSON array of platform names (e.g., `["instagram_feed", "twitter"]`)
- `uid` (required): Firebase user ID
- `reference_image` (optional): Product image file (PNG/JPEG, max 10MB)

**Headers**:
- `Authorization: Bearer {firebase_id_token}` (required)

**Response**: Returns task list with status `pending_approval`

**New Feature**: When `reference_image` is provided:
1. Uploads image to Cloud Storage
2. Analyzes image with Gemini Vision API (product type, colors, composition, mood, brand elements)
3. Incorporates analysis into task list generation for visually consistent marketing assets

### POST /api/approve

Approve pending job and trigger asset generation.

**Content-Type**: `application/json`

**Request Body**:
```json
{
  "event_id": "01ABCDEF...",
  "uid": "firebase_user_id"
}
```

**Headers**:
- `Authorization: Bearer {firebase_id_token}` (required)

### GET /health

Health check for Cloud Run.

### GET /docs

OpenAPI documentation.

## Development

### Setup

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### Run Locally

```bash
# With mock services (no real API calls)
uv run uvicorn app.main:app --reload --port 8000

# With real services (requires credentials)
# Set USE_MOCK_GEMINI=false, USE_MOCK_FIRESTORE=false in .env
uv run uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit

# Run with coverage
uv run pytest --cov=app
```

### Code Quality

```bash
# Format code
uv run black .
uv run ruff check . --fix

# Type check
uv run mypy app/
```

## Mock Mode

The service supports mock mode for rapid development:

- `USE_MOCK_GEMINI=true` - Mock AI responses (no Vertex AI calls)
- `USE_MOCK_STORAGE=true` - Mock Cloud Storage (no real uploads)
- `USE_MOCK_FIRESTORE=true` - In-memory storage (no Firestore)
- `USE_MOCK_PUBSUB=true` - Mock message publishing (no Pub/Sub)

### Integration Testing

Run integration tests with real Gemini Vision API:

```bash
# Requires: USE_MOCK_GEMINI=false in .env
uv run python test_reference_image_integration.py
```

This validates:
- Gemini Vision API image analysis (real API call)
- Task list generation with reference context
- Analysis quality and context incorporation

## Deployment

### Cloud Run

```bash
gcloud run deploy promote-strategy-agent \
  --source=. \
  --region=asia-northeast1 \
  --service-account=strategy-agent-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars=PROJECT_ID=xxx,PUBSUB_TOPIC=autonomy-tasks \
  --no-allow-unauthenticated
```

## Architecture

The Strategy Agent implements the first half of the HITL workflow:

1. **Strategize**: User submits goal → Gemini generates task list → Save as `pending_approval`
2. **Approve**: User approves → Firestore transaction (`pending_approval` → `processing`) → Publish to Pub/Sub

The approval step uses atomic transactions to prevent duplicate processing.
