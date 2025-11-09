# Hackathon Build Plan - AI Agents Track

**Target**: Cloud Run Hackathon - Best of AI Agents Track ($8,000 + $1,000 credits)

## Core Innovation
Multi-agent HITL workflow with two AI agents communicating via Pub/Sub:
- **Strategy Agent**: Plans marketing campaigns using Gemini
- **Creative Agent**: Executes approved plans, generates assets

## Technology Stack (Optimized for Prototyping)

### Backend Services
- **Language**: Python 3.11+ (FastAPI)
- **AI Models**: Vertex AI (Gemini for text, Imagen for images)
- **Message Queue**: Cloud Pub/Sub
- **Database**: Firestore (real-time, serverless)
- **Storage**: Cloud Storage
- **Auth**: Firebase Authentication
- **Deployment**: Cloud Run

### Frontend
- **Framework**: Next.js 14 (App Router)
- **UI**: Tailwind CSS + shadcn/ui (rapid prototyping)
- **Auth**: Firebase JS SDK
- **State**: Firestore real-time listeners

### Development Tools
- **Local Testing**: Firebase Emulator Suite
- **Python**: uv (fast package management)
- **Node**: pnpm (fast package management)
- **Environment**: python-dotenv / next.config.js

## Build Phases (Incremental)

### Phase 0: Foundation (Do First) ✅ COMPLETED
**Goal**: Set up tooling and define agent contract

- [x] Project structure (`/strategy-agent`, `/creative-agent`, `/frontend`)
- [x] Pydantic schemas (task list = agent communication contract)
- [x] Cloud project setup (Firestore, Pub/Sub, Storage)
- [x] Environment configuration (.env templates)

**Status**: PR #3 - All foundation complete with shared schemas package

---

### Phase 1: Strategy Agent (Core Innovation) ✅ COMPLETED
**Goal**: Demonstrate AI planning + HITL approval

- [x] FastAPI app structure
- [x] `/strategize` endpoint
  - [x] Gemini integration
  - [x] Task list generation
  - [x] Firestore write (status: pending_approval)
- [x] `/approve` endpoint (HITL core)
  - [x] Firebase ID Token verification
  - [x] Firestore transaction (pending_approval → processing)
  - [x] Pub/Sub publish (idempotent with retry + rollback)
- [x] Local testing with mock Gemini responses
- [x] **BONUS**: Retry logic with exponential backoff
- [x] **BONUS**: Rollback mechanism on Pub/Sub failure
- [x] **BONUS**: Configurable timeouts for LLM calls

**Status**: PR #3 - 14 passing tests, production-ready

---

### Phase 2: Creative Agent (Multi-Agent Communication) ✅ COMPLETED
**Goal**: Demonstrate agent-to-agent communication via Pub/Sub

- [x] FastAPI app structure
- [x] Pub/Sub push endpoint (`/api/consume`)
  - [x] Token verification (constant-time comparison)
  - [x] Message parsing
- [x] Copy generation
  - [x] Gemini API for caption generation
  - [x] Multiple style variants
  - [x] Robust regex parsing for LLM output
- [x] Image generation
  - [x] Imagen API integration
  - [x] Prompt engineering from task list
  - [x] Mock fallback with placeholder images
- [x] Firestore updates (status: completed)
- [x] Cloud Storage uploads
- [x] **BONUS**: Parallel asset generation (2-3x speedup)
- [x] **BONUS**: Idempotent message handling
- [x] **BONUS**: Video brief generation (text-only, Veo ready)

**Status**: PR #3 - 24 passing tests, production-ready

---

### Phase 3: Minimal Frontend (User Interface) ✅ COMPLETED
**Goal**: Working demo for "Try it Out" link

- [x] Firebase Auth setup (Google login)
- [x] Goal input page
- [x] Approval UI (shows pending plan)
- [x] Results dashboard (displays generated assets)
- [x] Firestore real-time listeners (status updates)
- [x] API client for Strategy Agent
- [x] **BONUS**: Error recovery and user feedback
- [x] **BONUS**: Clickable asset URLs
- [x] **BONUS**: Real-time status tracking

**Status**: PR #3 - Next.js app with full HITL workflow

---

### Phase 4: Deployment (Cloud Run) 🚧 READY BUT NOT DEPLOYED
**Goal**: Public demo URL for submission

- [x] Strategy Agent → Cloud Run ready (Dockerfile, .dockerignore)
- [x] Creative Agent → Cloud Run ready (Pub/Sub push subscription pattern)
- [x] Frontend → Cloud Run ready (or Vercel deployment)
- [x] Firestore security rules (firestore.rules)
- [x] IAM service accounts (least privilege - documented)
- [x] Environment variables configuration (.env.example files)

**Status**: All code ready, deployment commands documented in README

**Remaining Work**:
- [ ] Actual deployment to Cloud Run (gcloud commands in README)
- [ ] Pub/Sub topic creation
- [ ] Pub/Sub subscription setup with push endpoint
- [ ] Domain/URL configuration for "Try it Out" link

---

## Rapid Prototyping Shortcuts

### What to Prioritize
- ✅ **Agent communication**: Core innovation for AI Agents Track
- ✅ **HITL workflow**: Unique value proposition
- ✅ **Working demo**: Complete flow > polished UI
- ✅ **Gemini + Imagen**: Show Vertex AI integration

### What to Defer
- ⏸️ Video generation (Veo) - time-intensive, optional
- ⏸️ Brand style guides - Milestone 3 feature
- ⏸️ Multi-user teams - Milestone 4 feature
- ⏸️ Analytics dashboard - Milestone 5 feature
- ⏸️ UI polish - function over form

### Development Patterns
- **Mock-first development**: Use mock responses initially, swap to real API
- **Environment flags**: `USE_MOCK_GEMINI=true` for faster iteration
- **Local emulators**: Firebase emulator for Firestore/Pub/Sub testing
- **Shared schemas**: Single source of truth for data models
- **Type safety**: Pydantic (Python) + Zod (TypeScript) for validation

## Local Development Flow

```bash
# Terminal 1: Firebase emulators
firebase emulators:start

# Terminal 2: Strategy Agent
cd strategy-agent
uv run uvicorn app.main:app --reload

# Terminal 3: Creative Agent
cd creative-agent
uv run uvicorn app.main:app --reload

# Terminal 4: Frontend
cd frontend
pnpm dev
```

## Testing Strategy

### Strategy Agent
- Unit: Mock Gemini responses
- Integration: Real Firestore emulator + Pub/Sub emulator
- E2E: Deploy to Cloud Run staging

### Creative Agent
- Unit: Mock Imagen/Gemini responses
- Integration: Real Pub/Sub message handling
- E2E: Trigger via real Strategy Agent approval

### Frontend
- Manual: Click through approval flow
- Integration: Mock Strategy Agent API

## Success Criteria (Minimum Viable Demo)

### For AI Agents Track Judging
1. ✅ Two distinct AI agents (Strategy + Creative) - **DONE**
2. ✅ Agents communicate via Pub/Sub (not direct API calls) - **DONE**
3. ✅ Both agents use Vertex AI (Gemini/Imagen) - **DONE**
4. 🚧 Deployed to Cloud Run - **CODE READY, NEEDS DEPLOYMENT**
5. ✅ Human-in-the-loop approval (innovation) - **DONE**
6. 🚧 Working "Try it Out" link - **NEEDS DEPLOYMENT**

**Code Completion**: 95% (all features implemented)
**Deployment Completion**: 0% (not yet deployed to Cloud Run)

### Example Demo Script (3 min)
1. **Problem** (30s): "AI automation is risky without human oversight"
2. **Solution** (30s): "Multi-agent HITL workflow"
3. **Demo** (90s):
   - Input goal → Strategy Agent generates plan
   - Human approves → Creative Agent executes
   - Show generated captions + image
4. **Tech** (30s): "Two Cloud Run services communicate via Pub/Sub, Gemini plans, Imagen creates"

## Current Status (Updated: November 09, 2025)

### ✅ What's Complete (Phases 0-3)
- **All core features implemented** and tested (62 passing tests)
- **Three-service architecture** fully functional
- **HITL workflow** with atomic transactions and rollback
- **Security hardening** complete (auth, CORS, secrets, timeouts)
- **Mock-first development** enables cost-free testing
- **Comprehensive error handling** and retry logic
- **Production-ready code** with CI/CD pipeline

### 🚧 What Remains (Phase 4)
**Only deployment tasks** - no code changes needed:

1. **Deploy Services to Cloud Run** (~15 minutes):
   ```bash
   # Commands are already in README.md
   gcloud run deploy strategy-agent --source=./strategy-agent ...
   gcloud run deploy creative-agent --source=./creative-agent ...
   ```

2. **Configure Pub/Sub** (~10 minutes):
   ```bash
   gcloud pubsub topics create autonomy-tasks
   gcloud pubsub subscriptions create creative-agent-sub ...
   ```

3. **Deploy Frontend** (~10 minutes):
   - Option A: Vercel (recommended for speed)
   - Option B: Cloud Run

4. **Test End-to-End** (~15 minutes):
   - Submit test goal
   - Verify approval workflow
   - Check asset generation

**Total Deployment Time**: ~50 minutes

### Next Immediate Action
Run deployment commands from README.md to get public demo URL for hackathon submission.
