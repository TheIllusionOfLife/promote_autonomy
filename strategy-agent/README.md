# Strategy Agent

AI-powered marketing strategy generation with Human-in-the-Loop approval.

## Overview

The Strategy Agent generates marketing task lists using Gemini AI and manages the approval workflow before asset generation begins.

## Endpoints

- `POST /api/strategize` - Generate marketing strategy from goal
- `POST /api/approve` - Approve pending job and trigger asset generation
- `GET /health` - Health check for Cloud Run
- `GET /docs` - OpenAPI documentation

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
- `USE_MOCK_FIRESTORE=true` - In-memory storage (no Firestore)
- `USE_MOCK_PUBSUB=true` - Mock message publishing (no Pub/Sub)

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
