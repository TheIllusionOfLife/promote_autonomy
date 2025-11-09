# Post-Merge Critical Actions

## Overview
After merging PR #5, there are critical security actions you must complete before the system is production-ready.

---

## ⚠️ CRITICAL Task 1: Handle Exposed Secret in Git History

### Background
The file `deployment-info.txt` containing a Pub/Sub secret was committed to git history in PR #5:
- **Exposed Secret**: `uT3qtYq14NK7W47v+i6ULdTd7mn5WmZ1UaL1BtXtVYo=`
- Even though we removed it from the current version, it's still in git history

### ✅ Good News: This Secret Is Not Actually Used!

**We switched to OIDC authentication**, so the `PUBSUB_SECRET_TOKEN` is **not used** by the system anymore. The Creative Agent validates OIDC tokens from the `pubsub-invoker` service account instead.

### What You Should Do

**Option 1: Do Nothing (Recommended for MVP)**
- The secret was never used in production
- We're using OIDC authentication instead
- The security model doesn't rely on this secret
- Risk: Someone could try to use it, but OIDC validation would reject them

**Option 2: Clean Git History (Paranoid but Thorough)**

If you want to completely remove the secret from git history:

```bash
# WARNING: This rewrites git history - coordinate with any collaborators!

# Install git-filter-repo (if not already installed)
# macOS:
brew install git-filter-repo

# Remove the file from all history
git filter-repo --path deployment-info.txt --invert-paths

# Force push the cleaned history
git push origin --force --all
git push origin --force --tags

# All collaborators must re-clone the repository!
```

**Option 3: Mark as Known and Move On**
- Document that this secret was never used
- Add a note that we use OIDC authentication
- Keep it for reference of the deployment script's output format

### Recommended Action
**Option 1** is fine for this project since:
1. The secret was generated but never deployed to production
2. We use OIDC authentication (service account email verification)
3. The secret can't be used to bypass OIDC checks

---

## ✅ Task 2: Verify Cloud Storage Bucket Configuration

The Creative Agent makes uploaded files permanently public. This requires specific bucket settings.

### Step 1: Check Bucket Configuration

```bash
# Set your bucket name
STORAGE_BUCKET="promote-autonomy-assets"

# Check if Public Access Prevention is enforced
gsutil pap get gs://$STORAGE_BUCKET

# Expected output: "Public access prevention is inherited" or "unspecified"
# NOT "Public access prevention is enforced"
```

### Step 2: Fix If Needed

**If you see "Public access prevention is enforced":**

```bash
# Set to inherited (allows public access)
gsutil pap set inherited gs://$STORAGE_BUCKET

# Verify
gsutil pap get gs://$STORAGE_BUCKET
```

### Step 3: Verify Service Account Permissions

```bash
# Check IAM policy
gsutil iam get gs://$STORAGE_BUCKET

# Look for creative-agent service account with storage.objectAdmin role
# or storage.objects.setIamPolicy permission
```

**If the service account is missing the role:**

```bash
# Grant storage.objectAdmin role
gsutil iam ch \
  serviceAccount:creative-agent@promote-autonomy.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://$STORAGE_BUCKET

# Verify
gsutil iam get gs://$STORAGE_BUCKET | grep creative-agent
```

### Step 4: Test End-to-End

The best way to verify everything works is to test the complete workflow:

```bash
# 1. Get your frontend URL
FRONTEND_URL=$(gcloud run services describe frontend \
  --region=asia-northeast1 \
  --format='value(status.url)')

echo "Frontend URL: $FRONTEND_URL"

# 2. Visit the frontend in your browser
open "$FRONTEND_URL"

# 3. Create a test campaign:
#    - Sign in with Google
#    - Enter a goal (e.g., "Promote our new coffee blend")
#    - Wait for strategy generation
#    - Approve the strategy
#    - Wait for asset generation

# 4. Check if assets were created and are public
gsutil ls -l gs://$STORAGE_BUCKET/

# 5. Test public access to a generated image
# Copy an image URL from the frontend (after job completes)
# For example: https://storage.googleapis.com/promote-autonomy-assets/EVENT_ID/image.png

# Test it:
curl -I "https://storage.googleapis.com/promote-autonomy-assets/EVENT_ID/image.png"

# Expected: HTTP/2 200 OK
# NOT: HTTP/2 403 Forbidden
```

---

## 📋 Quick Verification Checklist

Run through this checklist to ensure everything is ready:

```bash
# 1. Bucket public access prevention
gsutil pap get gs://promote-autonomy-assets
# ✅ Should show "inherited" or "unspecified" (NOT "enforced")

# 2. Service account permissions
gsutil iam get gs://promote-autonomy-assets | grep creative-agent
# ✅ Should show roles/storage.objectAdmin or similar

# 3. Creative Agent is deployed and healthy
curl "$(gcloud run services describe creative-agent --region=asia-northeast1 --format='value(status.url)')/health"
# ✅ Should return: {"status":"healthy","service":"creative-agent",...}

# 4. Strategy Agent is deployed and healthy
curl "$(gcloud run services describe strategy-agent --region=asia-northeast1 --format='value(status.url)')/health"
# ✅ Should return: {"status":"healthy","service":"strategy-agent",...}

# 5. Frontend is deployed and accessible
open "$(gcloud run services describe frontend --region=asia-northeast1 --format='value(status.url)')"
# ✅ Should open in browser and show login page

# 6. Pub/Sub subscription is configured with OIDC
gcloud pubsub subscriptions describe promote-autonomy-tasks \
  --format='get(pushConfig.oidcToken)'
# ✅ Should show service account email (pubsub-invoker@promote-autonomy.iam.gserviceaccount.com)
```

---

## 🔍 Troubleshooting

### Issue: "Public access prevention is enforced"

**Symptom**: `gsutil pap get` shows "enforced"

**Solution**:
```bash
# Try to set to inherited
gsutil pap set inherited gs://promote-autonomy-assets

# If it fails with organization policy error:
# Your organization has a policy preventing public access
# You have two options:
# 1. Request an exception from your org admin
# 2. Use a different bucket not under the org policy
# 3. Implement signed URLs instead (requires code changes)
```

### Issue: Upload succeeds but files return 403

**Symptom**: Files are uploaded but not publicly accessible

**Cause**: Service account lacks permission to make objects public

**Solution**:
```bash
# Grant storage.objectAdmin role
gsutil iam ch \
  serviceAccount:creative-agent@promote-autonomy.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://promote-autonomy-assets
```

### Issue: Pub/Sub messages not reaching Creative Agent

**Symptom**: Strategy approved but no assets generated

**Check logs**:
```bash
# Creative Agent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=creative-agent" \
  --limit=20 \
  --format=json

# Look for:
# - "Invalid OIDC token" errors
# - "Invalid service account" errors
# - "POST 401" or "POST 403" errors
```

**Solution**:
```bash
# Verify Pub/Sub subscription is configured with OIDC
gcloud pubsub subscriptions describe promote-autonomy-tasks

# Should show:
# pushConfig:
#   oidcToken:
#     serviceAccountEmail: pubsub-invoker@promote-autonomy.iam.gserviceaccount.com
#   pushEndpoint: https://creative-agent-XXX.run.app/api/consume

# If missing, update it:
CREATIVE_AGENT_URL=$(gcloud run services describe creative-agent \
  --region=asia-northeast1 \
  --format='value(status.url)')

gcloud pubsub subscriptions update promote-autonomy-tasks \
  --push-endpoint="${CREATIVE_AGENT_URL}/api/consume" \
  --push-auth-service-account=pubsub-invoker@promote-autonomy.iam.gserviceaccount.com
```

---

## 🎯 What Success Looks Like

After completing these steps and testing:

1. ✅ You can sign in to the frontend
2. ✅ You can create a campaign and see the strategy
3. ✅ After approval, the job status changes to "processing"
4. ✅ Assets are generated (captions, image, video brief)
5. ✅ Asset URLs are publicly accessible without authentication
6. ✅ Job status updates to "completed"

**Example of successful output:**

```json
{
  "event_id": "01K9MG492QAPCW30EMT60MV380",
  "status": "completed",
  "captions_url": "https://storage.googleapis.com/.../captions.json",
  "image_url": "https://storage.googleapis.com/.../image.png",
  "video_url": "https://storage.googleapis.com/.../video_brief.txt"
}
```

All URLs should be directly accessible in a browser without authentication.

---

## 📚 Related Documentation

- [Storage Security Model](./docs/storage-security.md) - Why we use permanent public URLs
- [Deployment Guide](./docs/deployment-guide.md) - Complete deployment process
- [Firebase Setup](./docs/firebase-setup.md) - Firestore and authentication setup
- [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md) - Step-by-step deployment validation

---

## 🚀 Next Steps

Once verification is complete:

1. **Monitor in Production**:
   ```bash
   # Watch all services
   gcloud logging tail "resource.type=cloud_run_revision"
   ```

2. **Set Up Alerting** (Optional):
   - Cloud Run error rate monitoring
   - Pub/Sub dead letter queue alerts
   - Storage bucket size alerts

3. **Document Your Deployment**:
   - Save URLs (frontend, agents)
   - Document any custom configurations
   - Note any organization-specific settings

4. **Test with Real Use Cases**:
   - Try different campaign goals
   - Test with various image sizes
   - Verify video brief quality

---

**Questions?**
- Check the troubleshooting section above
- Review the deployment guide
- Check Cloud Run logs for specific error messages
