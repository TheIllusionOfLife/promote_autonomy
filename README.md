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

```
Frontend (Next.js, Cloud Run)
│   └─ Login → Goal input → Approval UI → Dashboard
│
Strategy Agent (FastAPI, Cloud Run)
│   ├─ /strategize → Generate task list
│   ├─ /approve → HITL approval + Pub/Sub publish
│   └─ Firestore writes (pending_approval → processing)
│
Creative Agent (FastAPI, Cloud Run)
    └─ Pub/Sub → Asset generation → Storage upload → Firestore update
```

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

Configure push subscriptions:
```bash
gcloud pubsub subscriptions create autonomy-tasks-sub \
  --topic=autonomy-tasks \
  --push-endpoint="https://creative-agent-xyz.run.app/pubsub" \
  --push-auth-token="your-secret"
```

---

## Security
- Firestore rules enforce **read-only for clients**.
- All state mutations are handled server-side.
- Pub/Sub push requests require shared verification token.
- Service accounts follow least-privilege principle.