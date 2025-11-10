# Infrastructure Configuration

This directory contains infrastructure-as-code scripts for Promote Autonomy.

## IAM Policies

### Service Accounts Required

1. **Strategy Agent** (`strategy-agent-sa@PROJECT_ID.iam.gserviceaccount.com`)
   - `roles/datastore.user` - Firestore read/write for job status
   - `roles/pubsub.publisher` - Publish tasks to Creative Agent
   - `roles/aiplatform.user` - Gemini API access for strategy generation
   - `roles/storage.objectCreator` - Upload reference images from users (PR #20)

2. **Creative Agent** (`creative-agent-sa@PROJECT_ID.iam.gserviceaccount.com`)
   - `roles/datastore.user` - Firestore read/write for job updates
   - `roles/storage.objectCreator` - Upload generated assets
   - `roles/aiplatform.user` - Imagen/Veo API access
   - `roles/pubsub.subscriber` - Receive task lists from Strategy Agent

### Setup Instructions

```bash
# Set your project ID
export PROJECT_ID=promote-autonomy

# Run IAM policy setup
./infra/setup-iam-policies.sh
```

### Verification

After running the setup script, verify IAM bindings:

```bash
# Check Strategy Agent permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:strategy-agent-sa@"

# Check Creative Agent permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:creative-agent-sa@"
```

## Infrastructure Changes

### PR #20: Storage Permissions for Reference Images

Added `roles/storage.objectCreator` to Strategy Agent service account to fix 403 errors when users upload product images via the Product Image (Optional) feature.

**Security Justification**:
- Strategy Agent needs write access to store user-uploaded reference images
- Images are stored in Cloud Storage for Creative Agent to access
- Alternative (signed URLs) would require additional complexity without security benefit

**Related Files**:
- `infra/setup-iam-policies.sh` - IAM policy definitions
- `strategy-agent/app/routers/strategize.py` - Reference image upload handler
- `creative-agent/app/services/imagen.py` - Reference image consumption

## Future Improvements

- [ ] Migrate to Terraform for full IaC management
- [ ] Add Cloud Storage bucket configuration
- [ ] Add Firestore security rules deployment
- [ ] Add Pub/Sub topic/subscription setup
- [ ] Add service account creation automation
