# Creative Agent

Creative Agent is a Pub/Sub push consumer that generates marketing assets (copy, images, videos) from task lists created by the Strategy Agent.

## Features

- **Copy Generation**: Creates social media captions using Gemini
- **Image Generation**: Produces images using Vertex AI Imagen
- **Video Briefs**: Generates detailed video production scripts
- **Cloud Storage**: Uploads all assets to Google Cloud Storage
- **Idempotent Processing**: Safely handles duplicate Pub/Sub messages
- **Mock-First Development**: Test without API costs using mock services

## Architecture

The Creative Agent receives task lists via Pub/Sub push subscription, generates all requested assets, uploads them to Cloud Storage, and updates Firestore job status to `completed`.

### State Flow

```
Pub/Sub message → Validate token → Verify job status → Generate assets → Upload to Storage → Update Firestore
```

## Installation

```bash
# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env

# Edit .env with your Google Cloud credentials
```

## Development

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_services.py -v
```

### Run Development Server

```bash
# With mock services (no API costs)
uv run uvicorn app.main:app --port 8001 --reload

# With real APIs
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json \
uv run uvicorn app.main:app --port 8001
```

### Mock vs Real Mode

The Creative Agent uses environment flags to switch between mock and real services:

- `USE_MOCK_IMAGEN=true`: Mock image generation (placeholder images)
- `USE_MOCK_VEO=true`: Mock video generation (text briefs only)
- `USE_MOCK_FIRESTORE=true`: In-memory Firestore
- `USE_MOCK_STORAGE=true`: In-memory file storage

## Deployment

### Cloud Run

```bash
gcloud run deploy creative-agent \
  --source=. \
  --region=asia-northeast1 \
  --service-account=creative-agent@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars=PROJECT_ID=your-project,STORAGE_BUCKET=your-bucket,PUBSUB_SECRET_TOKEN=your-token \
  --set-env-vars=USE_MOCK_IMAGEN=false,USE_MOCK_VEO=false,USE_MOCK_FIRESTORE=false,USE_MOCK_STORAGE=false \
  --no-allow-unauthenticated
```

### Pub/Sub Push Subscription

```bash
gcloud pubsub subscriptions create creative-agent-sub \
  --topic=autonomy-tasks \
  --push-endpoint=https://creative-agent-URL/api/consume \
  --push-auth-service-account=invoker@PROJECT_ID.iam.gserviceaccount.com
```

## API Reference

### POST /api/consume

Pub/Sub push endpoint for task consumption.

**Headers:**
- `Authorization: Bearer <PUBSUB_SECRET_TOKEN>`

**Request Body (Pub/Sub format):**
```json
{
  "message": {
    "data": "<base64-encoded-JSON>"
  },
  "subscription": "projects/.../subscriptions/..."
}
```

**Decoded message data:**
```json
{
  "event_id": "01ABC123...",
  "task_list": {
    "goal": "Marketing goal",
    "captions": {"n": 3, "style": "professional"},
    "image": {"prompt": "Image description", "size": "1024x1024"},
    "video": {"prompt": "Video concept", "duration_sec": 30}
  }
}
```

**Response:**
```json
{
  "status": "success",
  "event_id": "01ABC123...",
  "outputs": {
    "captions": "https://storage.googleapis.com/.../captions.json",
    "image": "https://storage.googleapis.com/.../image.png",
    "video": "https://storage.googleapis.com/.../video_brief.txt"
  }
}
```

## Testing with real APIs

See the Strategy Agent README for Google Cloud setup instructions. The Creative Agent requires:

- Vertex AI API enabled
- Cloud Storage bucket created
- Service account with appropriate permissions

## License

MIT
