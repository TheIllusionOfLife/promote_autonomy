# Deployment Guide - Cloud Run Hackathon

This guide provides everything you need to deploy Promote Autonomy to Google Cloud Run.

---

## 📁 Deployment Files Created

1. **`deploy.sh`** - Automated deployment script (main tool)
2. **`DEPLOYMENT_CHECKLIST.md`** - Step-by-step checklist to follow
3. **`docs/firebase-setup.md`** - Firebase initialization guide
4. **`docs/deployment-guide.md`** - This file (overview and reference)

---

## 🚀 Quick Start (50 minutes total)

### Option 1: Fast Track (Recommended)

```bash
# 1. Firebase setup (10 min)
#    Follow: docs/firebase-setup.md
firebase init
# Create frontend/.env.local with Firebase config

# 2. Run deployment script (40 min)
./deploy.sh
# Enter bucket name when prompted
# Wait for all services to deploy

# 3. Add frontend domain to Firebase (2 min)
#    Firebase Console → Authentication → Settings → Authorized domains

# 4. Test your deployment
#    Visit the frontend URL and complete a workflow
```

### Option 2: Step-by-Step

Follow `DEPLOYMENT_CHECKLIST.md` for detailed checkboxes and validation at each step.

---

## 📋 What Gets Deployed

| Component | Service | URL Pattern | Permissions |
|-----------|---------|-------------|-------------|
| **Frontend** | Cloud Run (Next.js) | `frontend-*.run.app` | Public |
| **Strategy Agent** | Cloud Run (FastAPI) | `strategy-agent-*.run.app` | Public |
| **Creative Agent** | Cloud Run (FastAPI) | `creative-agent-*.run.app` | Pub/Sub only |
| **Storage** | Cloud Storage | `gs://YOUR-BUCKET` | Service accounts |
| **Queue** | Pub/Sub topic + subscription | `creative-tasks` | Backend only |
| **Database** | Firestore (already exists) | - | Service accounts |

---

## 🔐 Service Accounts Created

The deployment script creates three service accounts:

1. **`strategy-agent-sa`**:
   - Firestore read/write
   - Pub/Sub publisher
   - Vertex AI (Gemini) access

2. **`creative-agent-sa`**:
   - Firestore read/write
   - Cloud Storage write
   - Vertex AI (Gemini, Imagen, Veo) access
   - Pub/Sub subscriber

3. **`pubsub-invoker`**:
   - Cloud Run invoker for Creative Agent
   - Used by Pub/Sub push subscription

---

## ⚙️ Environment Variables

### Automatically Set by Script

| Variable | Value | Purpose |
|----------|-------|---------|
| `PROJECT_ID` | `promote-autonomy` | GCP project identifier |
| `LOCATION` | `asia-northeast1` | Deployment region |
| `STORAGE_BUCKET` | User-provided | Asset storage location |
| `PUBSUB_TOPIC` | `creative-tasks` | Message queue name |
| `PUBSUB_SECRET_TOKEN` | Auto-generated | Security token |
| `USE_MOCK_*` | `false` | Enable real APIs |

### Model Versions (Updated to Latest)

| Model | Version | Purpose |
|-------|---------|---------|
| Gemini | `gemini-2.5-flash` | Strategy + copy generation |
| Imagen | `imagen-4.0-generate-001` | Image generation |
| Veo | `veo-3.0-generate-001` | Video briefs (text only) |

---

## 🧪 Testing Your Deployment

### 1. Basic Connectivity Test

```bash
# Test Strategy Agent health endpoint (if implemented)
curl https://YOUR-STRATEGY-URL/health

# Check Frontend is accessible
curl -I https://YOUR-FRONTEND-URL
```

### 2. End-to-End Workflow Test

1. Visit frontend URL
2. Sign in with Google
3. Submit goal: "Launch new eco-friendly product"
4. Wait for plan generation (~5-10 sec)
5. Click "Approve"
6. Wait for asset generation (~30-60 sec)
7. Verify outputs displayed

### 3. Monitor Logs in Real-Time

```bash
# Strategy Agent (watch approval flow)
gcloud run services logs tail strategy-agent --region=asia-northeast1

# Creative Agent (watch asset generation)
gcloud run services logs tail creative-agent --region=asia-northeast1

# Frontend (watch user interactions)
gcloud run services logs tail frontend --region=asia-northeast1
```

---

## 📊 Cost Estimates

Based on hackathon demo usage (assuming 10-20 test runs):

| Service | Estimated Cost |
|---------|----------------|
| Cloud Run (3 services) | $0.50 (within free tier) |
| Firestore | $0.00 (free tier) |
| Cloud Storage | $0.01 |
| Pub/Sub | $0.00 (free tier) |
| Vertex AI Gemini | $0.20 (20 requests @ $0.01/req) |
| Vertex AI Imagen | $0.40 (20 images @ $0.02/image) |
| **Total** | **~$1.11** |

---

## 🔍 Troubleshooting

### Deployment Script Fails

**Error**: `gcloud: command not found`
**Fix**: Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install

**Error**: `.firebaserc not found`
**Fix**: Run `firebase init` first (see `docs/firebase-setup.md`)

**Error**: `Permission denied on Firestore`
**Fix**: Ensure you're authenticated: `gcloud auth login`

### Runtime Errors

**Error**: CORS errors in browser console
**Fix**: Check `FRONTEND_URL` is set correctly in backend services

**Error**: "Authentication required" on frontend
**Fix**: Add frontend domain to Firebase authorized domains

**Error**: Assets not generating
**Fix**:
1. Check Creative Agent logs for errors
2. Verify Pub/Sub subscription exists: `gcloud pubsub subscriptions describe creative-agent-sub`
3. Check Pub/Sub permissions for invoker SA

**Error**: Vertex AI quota exceeded
**Fix**: Services fall back to mock mode gracefully (check logs)

### Check Service Health

```bash
# List all Cloud Run services
gcloud run services list --region=asia-northeast1

# Check service details
gcloud run services describe strategy-agent --region=asia-northeast1

# Check Pub/Sub subscription
gcloud pubsub subscriptions describe creative-agent-sub

# List storage bucket contents
gsutil ls gs://YOUR-BUCKET-NAME/
```

---

## 🎯 Hackathon Demo Script (3 minutes)

### 1. Introduction (30 seconds)

"Promote Autonomy solves a critical problem: AI automation needs human oversight. Our multi-agent system generates marketing strategies and assets, but requires explicit human approval before execution."

### 2. Architecture (30 seconds)

"We built three independent Cloud Run services:
- Strategy Agent plans campaigns using Gemini
- Human approves via our Next.js frontend
- Creative Agent executes, generating copy and images with Imagen
- All communicate via Pub/Sub for scalable, decoupled design"

### 3. Live Demo (90 seconds)

1. **Input** (15s): "Let me enter a marketing goal: 'Launch eco-friendly water bottle'"
2. **Generation** (15s): "Strategy Agent uses Gemini to create a multi-channel plan"
3. **HITL** (20s): "Here's the HITL innovation - I review the plan before any execution. I can see suggested captions, image prompts, and video concepts. I approve."
4. **Execution** (30s): "Creative Agent receives the approved plan via Pub/Sub, generates assets in parallel, and updates Firestore in real-time. Here are the results."
5. **Show Assets** (10s): "Marketing captions, AI-generated image, and video brief - all production-ready."

### 4. Technical Highlights (30 seconds)

"Key innovations:
- Atomic Firestore transactions prevent duplicate executions
- Pub/Sub decouples agents for scalability
- Fallback patterns ensure reliability even with API quota limits
- Real-time updates via Firestore listeners
- All deployed on Cloud Run for serverless scalability"

---

## 📝 Post-Deployment Checklist

After successful deployment:

- [ ] Save `deployment-info.txt` (contains all URLs and secrets)
- [ ] Test end-to-end workflow 3+ times
- [ ] Practice demo script
- [ ] Take screenshots for hackathon submission
- [ ] Prepare architecture diagram (use CLAUDE.md or README)
- [ ] Document HITL workflow in submission
- [ ] Submit hackathon entry with frontend URL

---

## 🧹 Cleanup After Hackathon

See `DEPLOYMENT_CHECKLIST.md` for cleanup commands to remove all resources.

**⚠️ Warning**: Cleanup deletes all generated assets and service accounts. Save any demo materials first.

---

## 📚 Additional Resources

- **Project README**: `README.md` - Architecture and local development
- **CLAUDE.md**: Architecture constraints and patterns
- **ROADMAP.md**: Future enhancements beyond MVP
- **session_handover.md**: Current project status

---

## ✅ Success Criteria

Your deployment is successful when:

1. ✅ All three services deployed and accessible
2. ✅ Frontend allows Google sign-in
3. ✅ Strategy generation works (Gemini API)
4. ✅ Approval workflow updates Firestore correctly
5. ✅ Creative Agent receives Pub/Sub messages
6. ✅ Assets generate successfully (copy, image, video brief)
7. ✅ Real-time updates visible in frontend
8. ✅ No errors in Cloud Run logs

**You're ready for the hackathon! 🚀**
