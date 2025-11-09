# Promote Autonomy

AI-powered marketing automation system with Human-in-the-Loop (HITL) approval for the Cloud Run Hackathon (AI Agents Track).

## Overview

Promote Autonomy is a multi-agent system that generates marketing strategies and assets using AI, requiring explicit human approval before execution. Built with three independent Cloud Run services communicating via Pub/Sub and sharing state through Firestore.

## Architecture

### Three-Service Design

```
┌─────────────┐       ┌──────────────────┐       ┌────────────────┐
│   Frontend  │──────▶│ Strategy Agent   │──────▶│ Creative Agent │
│  (Next.js)  │       │   (FastAPI)      │       │   (FastAPI)    │
└─────────────┘       └──────────────────┘       └────────────────┘
      │                       │                          │
      │                       │                          │
      └───────────────────────┴──────────────────────────┘
                              │
                        ┌─────▼─────┐
                        │ Firestore │
                        └───────────┘
```

**Frontend**: Client-side Firebase app with read-only Firestore access
**Strategy Agent**: Generates task lists via Gemini, handles approval workflow
**Creative Agent**: Pub/Sub consumer generating assets (copy, images, videos)

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

## Project Structure

```
promote-autonomy/
├── shared/                 # Shared Pydantic schemas (22 tests)
│   ├── src/promote_autonomy_shared/
│   │   └── schemas.py     # TaskList, Job, JobStatus models
│   └── tests/
├── strategy-agent/         # Strategy generation service (12 tests)
│   ├── app/
│   │   ├── routers/       # /strategize, /approve endpoints
│   │   ├── services/      # Gemini, Firestore, Pub/Sub
│   │   └── core/          # Configuration
│   └── tests/
├── creative-agent/         # Asset generation service (24 tests)
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

**Total: 62 passing tests** across all Python services (shared: 24, strategy: 14, creative: 24).

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
- ✅ Two communicating agents (Strategy → Creative via Pub/Sub)
- ✅ Cloud Run deployment
- ✅ Human-in-the-Loop approval workflow
- ✅ Vertex AI integration (Gemini, Imagen, Veo)

**MVP Features**:
- Marketing strategy generation
- Asset creation (copy, images, video briefs)
- Real-time status updates
- Approval workflow with Firestore transactions

## Project Status

**Live Demo**: https://frontend-909635873035.asia-northeast1.run.app

**Current Status**:
- ✅ **Code**: 100% complete (62/62 tests passing)
- ✅ **Deployment**: Fully deployed to Cloud Run (all 3 services live)
- ✅ **End-to-End Testing**: Verified working in production
- ✅ **Hackathon Ready**: Public demo URL available

**Documentation**:
- **Deployment Info**: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for service URLs, health checks, and production verification
- **Future Features**: See [FEATURE_ROADMAP.md](FEATURE_ROADMAP.md) for planned enhancements
- **Historical Docs**: Archived planning documents in [docs/archive/](docs/archive/)
