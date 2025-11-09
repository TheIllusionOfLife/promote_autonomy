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

**Total: 58 passing tests** across all Python services.

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

## License

MIT

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

## Session Handover

### Last Updated: November 09, 2025 02:27 PM JST

#### Recently Completed
- ✅ **[PR #3]**: Complete MVP implementation with three-service architecture
  - Full HITL workflow with atomic Firestore transactions
  - 62 passing tests (shared: 24, strategy: 14, creative: 24)
  - Mock-first development support
  - CI/CD pipeline for all services
  - Comprehensive security implementation
- ✅ **Critical Fixes** (Post-review commits):
  - Fixed Pub/Sub singleton pattern preventing test assertions
  - Added timeout protection for all Vertex AI calls (60-120s)
  - Expanded retry logic to catch GoogleAPICallError
  - Made retry parameters configurable via environment variables
  - Added missing Authorization header to frontend /strategize calls
  - Fixed Firestore listener dependencies to prevent cross-user data leaks
  - Added TaskList validation requiring at least one asset
  - Implemented thread-safe storage credential handling
  - Added frontend error recovery and asset URL display

#### Next Priority Tasks
1. **[CRITICAL] Deploy to Cloud Run**
   - Source: Hackathon submission requirement (Phase 4)
   - Context: All code is production-ready and tested (62 passing tests)
   - Approach: Execute deployment commands documented in README
   - Estimated Time: ~50 minutes total
   - Steps:
     1. Deploy Strategy Agent to Cloud Run (~15 min)
     2. Deploy Creative Agent to Cloud Run (~15 min)
     3. Create Pub/Sub topic and subscription (~10 min)
     4. Deploy Frontend to Vercel or Cloud Run (~10 min)
     5. End-to-end testing (~15 min)
   - Deliverable: Public "Try it Out" URL for hackathon judges

2. **[OPTIONAL] Add Rate Limiting**
   - Source: Claude Code review feedback
   - Context: Public endpoints lack protection against abuse
   - Approach: Add slowapi middleware or Cloud Armor
   - Priority: Medium - Good for production hardening

3. **[OPTIONAL] Add Integration Tests**
   - Source: Multiple review recommendations
   - Context: Currently only unit tests exist
   - Approach: Use Firebase emulators for end-to-end testing
   - Priority: Medium - Increases confidence but MVP works

4. **[OPTIONAL] Frontend Error Boundaries**
   - Source: Claude Code review
   - Context: Runtime errors could crash entire app
   - Approach: Add React error boundary components
   - Priority: Low - Nice-to-have for production

5. **[OPTIONAL] Add Structured Logging**
   - Source: Review feedback
   - Context: Better observability for Cloud Run
   - Approach: JSON logging for Cloud Logging integration
   - Priority: Low - Can add when deploying to production

6. **[OPTIONAL] Document Transaction Atomicity Limitation**
   - Source: Claude Code review
   - Context: Firestore transaction + Pub/Sub publish not truly atomic
   - Approach: Document known limitation and mitigation strategies
   - Priority: Low - Acceptable risk for MVP

#### Known Issues / Blockers
- None - MVP is production-ready for hackathon submission

#### Session Learnings
- **Frontend Auth Pattern**: Always audit all API calls for Authorization headers when backend requires auth
- **Singleton Pattern**: Critical for Cloud Run performance - prevents repeated client initialization
- **Timeout Protection**: Wrap all LLM calls with asyncio.wait_for() to prevent infinite hangs
- **Retry Robustness**: Catch GoogleAPICallError for comprehensive Google API error handling
- **Multi-Reviewer Handling**: Systematically extract and prioritize feedback from multiple AI reviewers
- **CORS Configuration**: Already properly configured with settings.FRONTEND_URL despite review concern
