# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Promote Autonomy is a cloud-based multi-agent marketing automation system with Human-in-the-Loop (HITL) approval. The system uses AI to generate promotional strategies and assets, requiring explicit human approval before execution.

**Core Architecture**: Three independent Cloud Run services communicate via Pub/Sub and share state through Firestore.

## System Architecture

### Three-Service Model

1. **Frontend (Next.js)**: Client-side read-only Firestore access, displays job state, sends approval actions to Strategy Agent
2. **Strategy Agent (FastAPI)**: Generates task lists via Gemini, handles `/approve` endpoint, publishes to Pub/Sub only after HITL approval
3. **Creative Agent (FastAPI)**: Pub/Sub push consumer, generates assets (copy/images/video), updates Firestore to `completed`

### Critical State Transitions

The HITL workflow enforces this state machine in Firestore `/jobs/{event_id}`:

```
pending_approval → (user approves) → processing → (assets generated) → completed
                → (user rejects) → rejected
```

**Key Rule**: Only the Strategy Agent's `/approve` endpoint can transition `pending_approval → processing`. This transition MUST use a Firestore transaction and publish to Pub/Sub atomically to prevent duplicate executions.

### Service Boundaries

- **Frontend**: NEVER writes to Firestore directly. All mutations go through Strategy Agent API.
- **Strategy Agent**: Owns job creation and approval logic. Must verify Firebase ID Tokens.
- **Creative Agent**: Idempotent by design. Receives task list via Pub/Sub, has no knowledge of HITL approval flow.

## Data Flow Pattern

1. User submits goal → Strategy Agent generates plan → saves as `pending_approval`
2. Frontend polls Firestore → displays plan → user clicks approve
3. Frontend calls `/approve` with ID Token → Strategy Agent validates → Firestore transaction → Pub/Sub publish
4. Creative Agent triggered → generates assets → uploads to Storage → sets `completed`

## Key Implementation Constraints

### Security Model

- **Firestore Rules**: Clients can read `/jobs/{event_id}` only if `uid` matches authenticated user. All writes require server-side service account.
- **API Authentication**: Strategy Agent `/approve` endpoint MUST verify Firebase ID Token before state transitions.
- **Pub/Sub Verification**: Creative Agent MUST validate OIDC token in push requests from Pub/Sub.

### Idempotency Requirements

- **Approval Endpoint**: Use Firestore transaction with conditional update (`status == "pending_approval"`). Return 409 if already processed.
- **Pub/Sub Publishing**: Only publish after successful transaction. If transaction fails, never publish.
- **Creative Agent**: Design to handle duplicate messages safely (Cloud Storage overwrites are acceptable).

### Fallback Strategy

When Vertex AI services (Imagen/Veo) are unavailable:
- Imagen unavailable → generate placeholder PNG with text overlay
- Veo unavailable → return script-only video brief (text description)
- Quota exceeded → text-only outputs, log error, set `status = failed`

## Service Account Permissions

Each service gets minimal IAM roles:
- **Frontend**: None (uses Firebase client SDK with user auth)
- **Strategy Agent**: Firestore write, Pub/Sub publish, Vertex AI (Gemini)
- **Creative Agent**: Firestore write, Storage write, Vertex AI (Imagen/Veo), Pub/Sub subscribe

## Development Workflow

### When Implementing Services

1. **Start with Firestore schema**: Define exact document structure in `/jobs/{event_id}` before coding
2. **Write Firestore security rules early**: Test read-only client access before building Frontend
3. **Strategy Agent first**: Build `/strategize` and `/approve` endpoints with transaction logic
4. **Creative Agent last**: This service is independent of HITL and simplest to implement
5. **Use Pydantic models**: Task list schema must be validated in both Strategy and Creative agents

### Directory Structure (Future)

```
/frontend              # Next.js (TypeScript)
  /app                 # App router pages
  /components          # React components
  /lib/firebase.ts     # Firebase client config

/strategy-agent        # FastAPI (Python 3.11+)
  /app
    /routers           # /strategize, /approve endpoints
    /models.py         # Pydantic task list schema
    /firestore.py      # Transaction logic
  requirements.txt

/creative-agent        # FastAPI (Python 3.11+)
  /app
    /generators        # Copy, image, video generation
    /models.py         # Same Pydantic schema
  requirements.txt

/infra                 # Terraform or gcloud scripts
  firestore.rules      # Security rules
```

## Task List Schema

The `task_list` object is the contract between Strategy Agent (producer) and Creative Agent (consumer):

```typescript
{
  "goal": string,
  "tasks": {
    "captions"?: { "n": number, "style": string },
    "image"?: { "prompt": string, "size": string },
    "video"?: { "prompt": string, "durationSec": number }
  }
}
```

Both agents must use identical Pydantic models to validate this schema.

## Cloud Run Deployment Pattern

All three services deploy independently:

```bash
gcloud run deploy SERVICE_NAME \
  --source=. \
  --region=asia-northeast1 \
  --service-account=SA_EMAIL \
  --set-env-vars=PROJECT_ID=xxx,PUBSUB_TOPIC=yyy
```

**Creative Agent requires**:
- `--no-allow-unauthenticated` with Pub/Sub push subscription configured to use OIDC token
- **Region Override**: Deploy to `us-central1` (not asia-northeast1) for VEO 3.0 video generation support
  ```bash
  gcloud run deploy creative-agent \
    --source=./creative-agent \
    --region=us-central1 \
    --service-account=creative-agent@PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars=LOCATION=us-central1
  ```

## Testing Strategy

- **Frontend**: Test Firestore read-only rules, mock Strategy Agent API
- **Strategy Agent**: Test transaction logic with Firestore emulator, mock Gemini responses
- **Creative Agent**: Test idempotency, mock Vertex AI services, verify Storage uploads
- **Integration**: Test full flow with Pub/Sub emulator

## Future Enhancements (See ROADMAP.md)

These are documented future features, not current implementation requirements:
- Pre-approval editing (Milestone 2)
- Brand Style Guide integration (Milestone 3)
- Multi-role workflows (Milestone 4)
- Performance feedback loop (Milestone 5)
