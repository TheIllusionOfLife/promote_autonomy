# Promote Autonomy
Multi-agent marketing automation system built with **Google Agent Development Kit (ADK)** and deployed on **Cloud Run**.  

## Overview
Promote Autonomy is a **multi-agent AI system** that generates marketing strategies and assets using Google's Agent Development Kit (ADK), requiring explicit human approval before execution.

**Key Innovation**: Combines ADK's multi-agent orchestration with Human-in-the-Loop (HITL) approval workflow to create multi-modal assets for platforms with multi-modal user input and direction.

### AI Agents Category Requirements
- ✅ **Google ADK Integration**: Creative Agent uses ADK coordinator with 3 specialized sub-agents
- ✅ **Multi-Agent Communication**: Strategy Agent → Pub/Sub → Creative Agent (ADK orchestrator)
- ✅ **Cloud Run Deployment**: 3 independent services (Frontend, Strategy Agent, Creative Agent)
- ✅ **Multiple Google AI Models**: Gemini 2.5 Flash, Imagen 4.0, Veo 3.0
- ✅ **Production-Ready**: 83 passing tests, full CI/CD, security hardening

## Architecture

📊 **[View Full Architecture Diagram](./architecture-diagram.svg)** | **[Detailed Documentation](./ARCHITECTURE.md)**
The architecture diagram shows the complete multi-agent system including ADK coordinator with 3 specialized sub-agents, data flow, and HITL workflow.

### HITL Workflow

1. **User Input** → Strategy Agent generates plan → `pending_approval`
2. **Frontend** displays plan → User reviews
3. **User Approval** → Strategy Agent validates → Firestore transaction + Pub/Sub publish
4. **Creative Agent** receives task → Generates assets → Updates Firestore to `completed`

### Critical State Machine

```
pending_approval → (approve) → processing → (assets done) → completed
                 → (reject)  → rejected
```

Only the Strategy Agent's `/approve` endpoint can transition to `processing` (atomic operation).

## Features

### Multi-Platform Asset Generation

Promote Autonomy generates platform-ready assets that meet each platform's specific requirements:

**Supported Platforms**:
- Instagram Feed (1:1 square, max 4MB)
- Instagram Story (9:16 vertical, max 4MB, max 15s video)
- X/Twitter (16:9, max 5MB)
- Facebook (1.91:1, max 8MB)
- LinkedIn (1.91:1, max 5MB, max 10min video)
- YouTube (16:9, various durations)

**How It Works**:
1. **Platform Selection**: Users select one or more target platforms in the frontend UI
2. **Constraint Calculation**: Strategy Agent calculates the most restrictive constraints across selected platforms:
   - Minimum video duration (e.g., Instagram Story's 15s limit)
   - Maximum file sizes (e.g., Instagram's 4MB limit)
   - First platform's aspect ratio (future: generate variants for each)
3. **Asset Generation**: Creative Agent generates assets matching these constraints:
   - **Images**: RealImageService uses specified aspect_ratio, applies JPEG compression to meet max_file_size_mb
   - **Videos**: RealVeoVideoService uses specified aspect_ratio, logs warnings if output exceeds max_file_size_mb

**Example**: Selecting Instagram Story + Twitter generates:
- Image: 1080x1920 (9:16), max 4MB (most restrictive)
- Video: 9:16 aspect ratio, max 15s duration, max 4MB
- Captions: Compatible with both platforms

**Platform Specifications** are defined in `shared/src/promote_autonomy_shared/schemas.py`:
```python
PLATFORM_SPECS = {
    Platform.INSTAGRAM_STORY: PlatformSpec(
        image_size="1080x1920",
        image_aspect_ratio="9:16",
        max_image_size_mb=4.0,
        video_aspect_ratio="9:16",
        max_video_length_sec=15,
        max_video_size_mb=4.0,
        caption_max_length=2200
    ),
    # ... more platforms
}
```

### Multi-Modal Input (Product Photos)

**NEW**: Upload product photos to generate visually consistent marketing assets.

**How It Works**:
1. **Image Upload**: Users upload a product image (PNG/JPEG, max 10MB) in the frontend
2. **Gemini Vision Analysis**: Strategy Agent analyzes the image using Gemini 2.5 Flash:
   - Product type and key features
   - Brand elements (logos, colors, visual style)
   - Composition, lighting, and mood
   - Marketing-relevant insights (200-400 words)
3. **Context Integration**: Analysis informs task list generation:
   - Image prompts incorporate product colors, style, and brand elements
   - Captions reference product features and visual identity
   - Generated assets maintain visual consistency with reference image
4. **Automatic Cleanup**: Reference images deleted after job completion to save storage costs

**Example**:
- Upload: Eco-friendly water bottle photo (green, outdoor setting)
- Analysis: "...forest green color, bamboo cap, outdoor hiking scene, eco-friendly messaging..."
- Generated Assets: Images show bottle in nature settings, captions emphasize sustainability

**API Integration**: `POST /api/strategize` accepts `reference_image` as multipart/form-data field

**Storage**: Reference images stored in Cloud Storage (`{event_id}/reference_image.{ext}`)

**Cleanup**: Deleted automatically by Creative Agent after job completion (creative-agent/app/routers/consume.py:226-234)

## Project Structure

```
promote-autonomy/
├── shared/                 # Shared Pydantic schemas (46 tests)
│   ├── src/promote_autonomy_shared/
│   │   └── schemas.py     # Platform, PlatformSpec, TaskList, Job models
│   └── tests/
├── strategy-agent/         # Strategy generation service (18 tests)
│   ├── app/
│   │   ├── routers/       # /strategize, /approve endpoints
│   │   ├── services/      # Gemini, Firestore, Pub/Sub
│   │   └── core/          # Configuration
│   └── tests/
├── creative-agent/         # Asset generation service (19 tests)
│   ├── app/
│   │   ├── routers/       # /consume (Pub/Sub push)
│   │   ├── services/      # Copy, Image, Video, Storage
│   │   └── core/          # Configuration
│   └── tests/
├── frontend/               # Next.js HITL interface
│   ├── app/               # App router pages
│   ├── lib/               # Firebase client, API, types
│   └── components/
├── firestore.rules         # Security rules (read-only clients)
├── firebase.json           # Firebase configuration
└── .github/workflows/      # CI/CD pipeline
    └── ci.yml             # Tests for all services
```

**Total: 83 passing tests** across all Python services (shared: 46, strategy: 18, creative: 19).

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Google Cloud project with:
  - Firestore enabled
  - Pub/Sub enabled
  - Vertex AI API enabled
  - Service account with appropriate permissions

### Development Setup

1. **Clone and install shared schemas**:
   ```bash
   cd shared
   uv sync
   ```

2. **Set up Strategy Agent**:
   ```bash
   cd strategy-agent
   cp .env.example .env
   # Edit .env with your Google Cloud credentials
   uv sync
   uv run pytest  # Run tests
   ```

3. **Set up Creative Agent**:
   ```bash
   cd creative-agent
   cp .env.example .env
   # Edit .env with your credentials
   uv sync
   uv run pytest  # Run tests
   ```

4. **Set up Frontend**:
   ```bash
   cd frontend
   npm install
   cp .env.local.example .env.local
   # Edit .env.local with Firebase config
   ```

### Running Locally

Terminal 1 (Strategy Agent):
```bash
cd strategy-agent
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json \
uv run uvicorn app.main:app --port 8000
```

Terminal 2 (Creative Agent):
```bash
cd creative-agent
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json \
uv run uvicorn app.main:app --port 8001
```

Terminal 3 (Frontend):
```bash
cd frontend
npm run dev  # Runs on http://localhost:3000
```

### Mock Mode vs Real APIs

Both agents support mock mode for rapid development:

**Strategy Agent** (`.env`):
```
USE_MOCK_GEMINI=true    # No Gemini API calls
USE_MOCK_FIRESTORE=true # In-memory database
USE_MOCK_PUBSUB=true    # No Pub/Sub publish
```

**Creative Agent** (`.env`):
```
USE_MOCK_IMAGEN=true    # Placeholder images
USE_MOCK_VEO=true       # Text briefs only
USE_MOCK_FIRESTORE=true # In-memory database
USE_MOCK_STORAGE=true   # No Cloud Storage uploads
```

## Testing

Run all tests:
```bash
# Shared schemas
cd shared && uv run pytest -v

# Strategy Agent
cd strategy-agent && uv run pytest -v

# Creative Agent
cd creative-agent && uv run pytest -v
```

Coverage:
```bash
uv run pytest --cov=app --cov-report=term-missing
```

## Deployment

### Deploy to Cloud Run

Each service deploys independently:

```bash
# Strategy Agent
gcloud run deploy strategy-agent \
  --source=./strategy-agent \
  --region=asia-northeast1 \
  --service-account=strategy-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars=PROJECT_ID=xxx,PUBSUB_TOPIC=autonomy-tasks

# Creative Agent
gcloud run deploy creative-agent \
  --source=./creative-agent \
  --region=asia-northeast1 \
  --service-account=creative-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars=PROJECT_ID=xxx,STORAGE_BUCKET=xxx \
  --no-allow-unauthenticated

# Frontend (or deploy to Vercel)
gcloud run deploy frontend \
  --source=./frontend \
  --region=asia-northeast1 \
  --allow-unauthenticated
```

### Pub/Sub Configuration

Create push subscription for Creative Agent:

```bash
gcloud pubsub topics create autonomy-tasks

gcloud pubsub subscriptions create creative-agent-sub \
  --topic=autonomy-tasks \
  --push-endpoint=https://creative-agent-URL/api/consume \
  --push-auth-service-account=invoker@PROJECT_ID.iam.gserviceaccount.com
```

### Firestore Security Rules

Deploy rules:
```bash
firebase deploy --only firestore:rules
```

## API Reference

### Strategy Agent

**POST /api/strategize**
- Generate marketing strategy from goal
- Returns: `event_id`, `status`, `task_list`

**POST /api/approve**
- Approve pending strategy
- Requires: Firebase ID Token
- Returns: `event_id`, `status`, `published`

### Creative Agent

**POST /api/consume**
- Pub/Sub push endpoint
- Requires: Secret token in Authorization header
- Generates assets and updates Firestore

## Security

- **Firestore**: Read-only client access, server-side writes only
- **API Auth**: `/approve` endpoint validates Firebase ID tokens
- **Pub/Sub**: Secret token validation for push endpoint
- **Service Accounts**: Minimal IAM permissions per service

## Development Patterns

- **Mock-first**: Develop without API costs
- **Protocol interfaces**: Easy testing with mock implementations
- **Singleton services**: Consistent state across requests
- **Atomic transactions**: HITL approval workflow integrity
- **Idempotent processing**: Safe duplicate message handling

## Contributing

1. Create feature branch from `main`
2. Make changes with tests
3. Run tests locally
4. Push and create PR
5. Wait for CI to pass

## Hackathon Notes

**Track**: AI Agents Track
**Requirements Met**:
- ✅ Multiple agents communication with ADK
- ✅ Cloud Run deployment

**MVP Features**:
- Marketing strategy generation
- Asset creation (copy, images, video briefs) with multi-modal input
- Real-time status updates
- Approval workflow with Firestore transactions

## Project Status

> **⚠️ Infrastructure Suspended (2025-12-19)**
>
> Cloud infrastructure has been shut down to reduce costs. The demo URL is no longer active.
> See [Infrastructure Suspension](#infrastructure-suspension-2025-12-19) section below for details on how to redeploy.

**Live Demo**: ~~https://frontend-909635873035.asia-northeast1.run.app/~~ (suspended)

**Current Status**:
- ✅ **Code**: 100% complete (83/83 tests passing)
- ⏸️ **Deployment**: Infrastructure suspended (can be redeployed)
- ✅ **Platform Support**: Multi-platform asset generation (Instagram, Twitter, Facebook, LinkedIn, YouTube)
- ✅ **End-to-End Testing**: Previously verified working in production
- ✅ **Hackathon Ready**: Code complete, deployment docs available

**Documentation**:
- **Deployment Info**: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for service URLs, health checks, and production verification
- **Future Features**: See [FEATURE_ROADMAP.md](FEATURE_ROADMAP.md) for planned enhancements
- **Historical Docs**: Archived planning documents in [docs/archive/](docs/archive/)

## Infrastructure Suspension (2025-12-19)

### Why Suspended?

The GCP infrastructure was shut down to eliminate ongoing costs. November 2025 billing showed:
- **Vertex AI**: ¥6,027 (image/video generation when users trigger the system)
- **Artifact Registry**: ¥55 (Docker image storage)
- **Cloud Run**: ¥16 (service hosting)
- **Cloud Storage**: ¥7 (asset storage)

To prevent unauthorized usage costs and storage fees, all resources were deleted.

### What Was Deleted

**Cloud Run Services** (4 services):
```bash
# Commands executed:
gcloud run services delete frontend --region=asia-northeast1 --quiet
gcloud run services delete strategy-agent --region=asia-northeast1 --quiet
gcloud run services delete creative-agent --region=asia-northeast1 --quiet
gcloud run services delete creative-agent --region=us-central1 --quiet
```

**Artifact Registry** (4 repositories, ~6GB Docker images):
```bash
gcloud artifacts repositories delete cloud-run-source-deploy --location=asia-northeast1 --quiet
gcloud artifacts repositories delete asia.gcr.io --location=asia --quiet
gcloud artifacts repositories delete us.gcr.io --location=us --quiet
gcloud artifacts repositories delete cloud-run-source-deploy --location=us-central1 --quiet
```

**Cloud Storage** (5 buckets, ~2.6GB):
```bash
gsutil -m rm -r gs://promote-autonomy-assets/
gsutil -m rm -r gs://promote-autonomy-veo-output/
gsutil -m rm -r gs://promote-autonomy_cloudbuild/
gsutil -m rm -r gs://run-sources-promote-autonomy-asia-northeast1/
gsutil -m rm -r gs://run-sources-promote-autonomy-us-central1/
```

### How to Redeploy

1. **Deploy Cloud Run services** (see [Deployment](#deploy-to-cloud-run) section):
   ```bash
   # Strategy Agent
   gcloud run deploy strategy-agent \
     --source=./strategy-agent \
     --region=asia-northeast1 \
     --service-account=strategy-sa@PROJECT_ID.iam.gserviceaccount.com \
     --set-env-vars=PROJECT_ID=promote-autonomy,PUBSUB_TOPIC=autonomy-tasks

   # Creative Agent
   gcloud run deploy creative-agent \
     --source=./creative-agent \
     --region=asia-northeast1 \
     --service-account=creative-sa@PROJECT_ID.iam.gserviceaccount.com \
     --set-env-vars=PROJECT_ID=promote-autonomy,STORAGE_BUCKET=promote-autonomy-assets \
     --no-allow-unauthenticated

   # Frontend
   gcloud run deploy frontend \
     --source=./frontend \
     --region=asia-northeast1 \
     --allow-unauthenticated
   ```

2. **Create Cloud Storage buckets**:
   ```bash
   gsutil mb -l asia-northeast1 gs://promote-autonomy-assets/
   gsutil mb -l asia-northeast1 gs://promote-autonomy-veo-output/
   ```

3. **Configure Pub/Sub** (if subscription was deleted):
   ```bash
   gcloud pubsub subscriptions create creative-agent-sub \
     --topic=autonomy-tasks \
     --push-endpoint=https://creative-agent-URL/api/consume \
     --push-auth-service-account=invoker@PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Update Frontend environment** with new service URLs in Cloud Run console or redeploy.

**Note**: Artifact Registry repositories and Cloud Build artifacts are automatically recreated when deploying with `--source`.
