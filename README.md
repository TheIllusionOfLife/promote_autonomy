# Promote Autonomy
AI-assisted marketing workflow with Human-in-the-Loop (HITL) approval, built on Google Cloud Run, Pub/Sub, Firebase, Firestore, and Vertex AI.

Promote Autonomy helps startups and creators turn high-level marketing goals into actionable promotional assets. The system uses:
- **AI strategy generation** (Gemini)
- **User approval gates** (HITL)
- **Async asset generation** (copy, images, optional video)
- **Multi-agent architecture** powered by Cloud Run and Pub/Sub

This repository contains all services and infrastructure required to run the Promote Autonomy MVP.

---

## Features
- AI-generated marketing strategy
- Human approval workflow before execution
- Multi-agent execution pipeline
- Automated generation of copy, images, and optional video
- Real-time Firestore updates for job progress
- Cloud Run–first design with scalable async processing

---

## Architecture Overview
Promote Autonomy consists of three core services:

**Frontend (Next.js, Cloud Run)**
- Provides login, goal input, and approval UI
- Displays real-time job status from Firestore
- Renders final asset dashboard

**Strategy Agent (FastAPI, Cloud Run)**
- Generates task lists via `/strategize` endpoint
- Handles HITL approval via `/approve` endpoint
- Publishes approved tasks to Pub/Sub
- Manages Firestore state transitions (pending_approval → processing)

**Creative Agent (FastAPI, Cloud Run)**
- Consumes Pub/Sub messages to generate assets
- Generates copy using Gemini, images using Imagen
- Uploads assets to Cloud Storage
- Updates Firestore with completion status

Additional components:
- Firebase Authentication
- Firestore (job state + metadata)
- Cloud Storage (binary assets)
- Pub/Sub topics for async execution

---

## Repository Structure
```
/ frontend              # Next.js UI
/ strategy-agent        # Strategy generation + approval API
/ creative-agent        # Pub/Sub consumer for asset generation
/ infra                 # Infra as code (optional)
/ docs                  # Specification + diagrams
```

---

## Getting Started
### Prerequisites
- Node.js 18+
- Python 3.11+
- Google Cloud project
- Firebase project (Auth + Firestore)
- Cloud SDK installed

### Clone
```bash
git clone https://github.com/your-org/promote-autonomy.git
cd promote-autonomy
```

---

## Deployment (Core Services)
Each service can be deployed independently to Cloud Run.

Example:
```bash
cd strategy-agent
gcloud run deploy promote-strategy \
  --source=. \
  --region=asia-northeast1 \
  --no-allow-unauthenticated
```

Configure push subscriptions with OIDC authentication:
```bash
gcloud pubsub subscriptions create autonomy-tasks-sub \
  --topic=autonomy-tasks \
  --push-endpoint="https://creative-agent-xyz.run.app/pubsub" \
  --push-auth-service-account=INVOKER_SERVICE_ACCOUNT_EMAIL
```

---

## Security
- Firestore rules enforce **read-only for clients**.
- All state mutations are handled server-side.
- Pub/Sub push requests use OIDC token authentication.
- Service accounts follow least-privilege principle.
