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

### Phase 0: Foundation (Do First)
**Goal**: Set up tooling and define agent contract

- [x] Project structure (`/strategy-agent`, `/creative-agent`, `/frontend`)
- [ ] Pydantic schemas (task list = agent communication contract)
- [ ] Cloud project setup (Firestore, Pub/Sub, Storage)
- [ ] Environment configuration (.env templates)

**Why First**: Agent contract defines all interfaces

---

### Phase 1: Strategy Agent (Core Innovation)
**Goal**: Demonstrate AI planning + HITL approval

- [ ] FastAPI app structure
- [ ] `/strategize` endpoint
  - Gemini integration
  - Task list generation
  - Firestore write (status: pending_approval)
- [ ] `/approve` endpoint (HITL core)
  - Firebase ID Token verification
  - Firestore transaction (pending_approval → processing)
  - Pub/Sub publish (idempotent)
- [ ] Local testing with mock Gemini responses

**Demo Value**: Shows human-in-the-loop safety pattern

---

### Phase 2: Creative Agent (Multi-Agent Communication)
**Goal**: Demonstrate agent-to-agent communication via Pub/Sub

- [ ] FastAPI app structure
- [ ] Pub/Sub push endpoint (`/pubsub`)
  - Token verification
  - Message parsing
- [ ] Copy generation
  - Gemini API for caption generation
  - Multiple style variants
- [ ] Image generation
  - Imagen API integration
  - Prompt engineering from task list
- [ ] Firestore updates (status: completed)
- [ ] Cloud Storage uploads

**Demo Value**: Shows async agent execution

---

### Phase 3: Minimal Frontend (User Interface)
**Goal**: Working demo for "Try it Out" link

- [ ] Firebase Auth setup (Google login)
- [ ] Goal input page
- [ ] Approval UI (shows pending plan)
- [ ] Results dashboard (displays generated assets)
- [ ] Firestore real-time listeners (status updates)
- [ ] API client for Strategy Agent

**Demo Value**: Complete end-to-end workflow

---

### Phase 4: Deployment (Cloud Run)
**Goal**: Public demo URL for submission

- [ ] Strategy Agent → Cloud Run
- [ ] Creative Agent → Cloud Run (Pub/Sub push subscription)
- [ ] Frontend → Cloud Run
- [ ] Firestore security rules
- [ ] IAM service accounts (least privilege)
- [ ] Environment variables configuration

**Demo Value**: Production deployment on Cloud Run

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
1. ✅ Two distinct AI agents (Strategy + Creative)
2. ✅ Agents communicate via Pub/Sub (not direct API calls)
3. ✅ Both agents use Vertex AI (Gemini/Imagen)
4. ✅ Deployed to Cloud Run
5. ✅ Human-in-the-loop approval (innovation)
6. ✅ Working "Try it Out" link

### Example Demo Script (3 min)
1. **Problem** (30s): "AI automation is risky without human oversight"
2. **Solution** (30s): "Multi-agent HITL workflow"
3. **Demo** (90s):
   - Input goal → Strategy Agent generates plan
   - Human approves → Creative Agent executes
   - Show generated captions + image
4. **Tech** (30s): "Two Cloud Run services communicate via Pub/Sub, Gemini plans, Imagen creates"

## Next Steps

Start with Phase 0 (foundation) immediately:
1. Create directory structure
2. Define Pydantic task list schema (agent contract)
3. Set up Firebase project + Pub/Sub topic
