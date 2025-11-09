# Cloud Run Deployment Checklist

Use this checklist to deploy Promote Autonomy to Google Cloud Run for the hackathon demo.

**Estimated Total Time**: ~50 minutes

---

## Before You Start

- [ ] You have Google Cloud Project: `promote-autonomy`
- [ ] You have `gcloud` CLI installed and authenticated
- [ ] You have `firebase` CLI installed (`npm install -g firebase-tools`)
- [ ] You're logged into Firebase (`firebase login`)

---

## Phase 1: Firebase Setup (~10 minutes)

Follow the guide: [`docs/firebase-setup.md`](docs/firebase-setup.md)

- [ ] Run `firebase init` (select Firestore only)
- [ ] Enable Google Authentication in Firebase Console
- [ ] Get Firebase config from Firebase Console (Web app settings)
- [ ] Create `frontend/.env.local` with Firebase credentials
- [ ] Deploy Firestore security rules (`firebase deploy --only firestore:rules`)
- [ ] Verify `.firebaserc` file exists

**🎯 Checkpoint**: You should have:
- ✅ `.firebaserc` file in project root
- ✅ `frontend/.env.local` with all Firebase config values
- ✅ Google sign-in enabled in Firebase Console

---

## Phase 2: Run Automated Deployment (~40 minutes)

### Step 1: Start Deployment Script

```bash
cd /Users/yuyamukai/dev/promote_autonomy
./deploy.sh
```

The script will:
1. Check prerequisites (Firebase config, gcloud)
2. Prompt for Cloud Storage bucket name
3. Enable Google Cloud APIs
4. Create service accounts with IAM roles
5. Create Cloud Storage bucket
6. Create Pub/Sub topic
7. Deploy Strategy Agent (~5 min build time)
8. Deploy Creative Agent (~5 min build time)
9. Configure Pub/Sub push subscription
10. Deploy Frontend (~5 min build time)
11. Update CORS settings

### Step 2: When Prompted

- [ ] Enter Cloud Storage bucket name (e.g., `promote-autonomy-assets`)
- [ ] Wait for deployments to complete
- [ ] Note the service URLs shown at the end

**🎯 Checkpoint**: Script should output:
- ✅ Frontend URL: `https://frontend-xxx.run.app`
- ✅ Strategy Agent URL: `https://strategy-agent-xxx.run.app`
- ✅ Creative Agent URL: `https://creative-agent-xxx.run.app`
- ✅ `deployment-info.txt` file created

---

## Phase 3: Manual Post-Deployment Steps (~5 minutes)

### Step 1: Add Frontend Domain to Firebase

1. Go to [Firebase Console → Authentication → Settings](https://console.firebase.google.com/project/promote-autonomy/authentication/settings)
2. Click **Authorized domains** tab
3. Click **Add domain**
4. Add your frontend Cloud Run domain (from deployment output)
   - Example: `frontend-abc123-uc.a.run.app`
5. Click **Add**

- [ ] Frontend domain added to Firebase authorized domains

### Step 2: Test End-to-End Workflow

1. Visit your Frontend URL
2. Click "Sign in with Google"
3. Enter a test marketing goal (e.g., "Launch new eco-friendly water bottle")
4. Wait for strategy generation (~5-10 seconds)
5. Review the plan and click "Approve"
6. Wait for asset generation (~30-60 seconds)
7. Verify generated assets appear

- [ ] Successfully signed in with Google
- [ ] Strategy generation works
- [ ] Approval workflow works
- [ ] Assets generated and displayed

**🎯 Checkpoint**: You should see:
- ✅ Generated marketing captions
- ✅ Generated image (or placeholder if Imagen quota exceeded)
- ✅ Video brief text
- ✅ Job status: "Completed"

---

## Phase 4: Monitor & Troubleshoot (If Needed)

### Check Service Logs

```bash
# Strategy Agent logs
gcloud run services logs read strategy-agent --region=asia-northeast1 --limit=50

# Creative Agent logs
gcloud run services logs read creative-agent --region=asia-northeast1 --limit=50

# Frontend logs
gcloud run services logs read frontend --region=asia-northeast1 --limit=50
```

### Common Issues

**Issue**: "Authentication required" on frontend
**Fix**: Check that frontend domain is in Firebase authorized domains

**Issue**: "CORS error" in browser console
**Fix**: Verify `FRONTEND_URL` is set correctly in backend services

**Issue**: Assets not generating
**Fix**:
1. Check Creative Agent logs for errors
2. Verify Pub/Sub subscription is active: `gcloud pubsub subscriptions describe creative-agent-sub`
3. Check service account permissions

**Issue**: Vertex AI quota exceeded
**Fix**: Services will fall back to mock mode or text-only outputs

---

## Phase 5: Hackathon Submission

- [ ] Frontend URL is public and working
- [ ] Prepared 3-minute demo script
- [ ] Tested demo flow end-to-end
- [ ] Documented architecture in submission
- [ ] Highlighted HITL innovation (key differentiator)

**Demo URL for Hackathon**: (Your Frontend URL from deployment)

---

## Deployment Complete! 🎉

Your service URLs are in `deployment-info.txt`.

### Quick Reference

**Frontend**: Your public demo URL
**Strategy Agent**: Backend API for plan generation
**Creative Agent**: Backend worker for asset generation

**Storage Bucket**: `gs://YOUR-BUCKET-NAME`
**Pub/Sub Topic**: `creative-tasks`
**Project**: `promote-autonomy`
**Region**: `asia-northeast1`

### Next Steps

1. ✅ Test the full workflow multiple times
2. ✅ Practice your hackathon demo
3. ✅ Monitor Cloud Run costs (should be minimal with free tier)
4. ✅ Submit hackathon entry with frontend URL

---

## Cleanup (After Hackathon)

To remove all deployed resources:

```bash
# Delete Cloud Run services
gcloud run services delete strategy-agent --region=asia-northeast1 --quiet
gcloud run services delete creative-agent --region=asia-northeast1 --quiet
gcloud run services delete frontend --region=asia-northeast1 --quiet

# Delete Pub/Sub resources
gcloud pubsub subscriptions delete creative-agent-sub --quiet
gcloud pubsub topics delete creative-tasks --quiet

# Delete Storage bucket (WARNING: deletes all assets)
gsutil rm -r gs://YOUR-BUCKET-NAME

# Delete service accounts (optional)
gcloud iam service-accounts delete strategy-agent-sa@promote-autonomy.iam.gserviceaccount.com --quiet
gcloud iam service-accounts delete creative-agent-sa@promote-autonomy.iam.gserviceaccount.com --quiet
gcloud iam service-accounts delete pubsub-invoker@promote-autonomy.iam.gserviceaccount.com --quiet
```
