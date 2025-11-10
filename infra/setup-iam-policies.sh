#!/bin/bash

# IAM Policy Setup for Promote Autonomy Services
# This script configures all required IAM roles for service accounts
# Run this after creating service accounts and before deploying services

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-promote-autonomy}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up IAM policies for Promote Autonomy services...${NC}"
echo "Project: $PROJECT_ID"
echo ""

# Strategy Agent Service Account
STRATEGY_SA="strategy-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${YELLOW}[1/2] Configuring Strategy Agent IAM roles...${NC}"
echo "Service Account: $STRATEGY_SA"

# Grant Firestore write access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$STRATEGY_SA" \
  --role="roles/datastore.user" \
  --condition=None

# Grant Pub/Sub publish access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$STRATEGY_SA" \
  --role="roles/pubsub.publisher" \
  --condition=None

# Grant Vertex AI user access (for Gemini)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$STRATEGY_SA" \
  --role="roles/aiplatform.user" \
  --condition=None

# Grant Cloud Storage object creator (for reference image uploads)
# Added in PR #20 to fix 403 errors when users upload product images
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$STRATEGY_SA" \
  --role="roles/storage.objectCreator" \
  --condition=None

echo -e "${GREEN}✓ Strategy Agent IAM roles configured${NC}"
echo ""

# Creative Agent Service Account
CREATIVE_SA="creative-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${YELLOW}[2/2] Configuring Creative Agent IAM roles...${NC}"
echo "Service Account: $CREATIVE_SA"

# Grant Firestore write access
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CREATIVE_SA" \
  --role="roles/datastore.user" \
  --condition=None

# Grant Cloud Storage write access (for generated assets)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CREATIVE_SA" \
  --role="roles/storage.objectCreator" \
  --condition=None

# Grant Vertex AI user access (for Imagen/Veo)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CREATIVE_SA" \
  --role="roles/aiplatform.user" \
  --condition=None

# Grant Pub/Sub subscriber access (for receiving tasks)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CREATIVE_SA" \
  --role="roles/pubsub.subscriber" \
  --condition=None

echo -e "${GREEN}✓ Creative Agent IAM roles configured${NC}"
echo ""
echo -e "${GREEN}All IAM policies configured successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Deploy services: ./deploy.sh"
echo "  2. Verify permissions by testing reference image upload"
echo ""
