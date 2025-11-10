#!/bin/bash

##############################################################################
# Promote Autonomy - Automated Cloud Run Deployment Script
#
# This script deploys all services to Google Cloud Run for the hackathon demo.
#
# Prerequisites:
# 1. Complete docs/firebase-setup.md guide
# 2. Have gcloud CLI installed and authenticated
# 3. Have frontend/.env.local configured with Firebase credentials
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_ID="promote-autonomy"
REGION="asia-northeast1"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Promote Autonomy - Cloud Run Deployment Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

##############################################################################
# STEP 0: Pre-flight Checks
##############################################################################

echo -e "${YELLOW}[STEP 0]${NC} Running pre-flight checks..."

# Check if Firebase is configured
if [ ! -f ".firebaserc" ]; then
    echo -e "${RED}ERROR: .firebaserc not found!${NC}"
    echo "Please run 'firebase init' first. See docs/firebase-setup.md"
    exit 1
fi

# Check if frontend .env.local exists
if [ ! -f "frontend/.env.local" ]; then
    echo -e "${RED}ERROR: frontend/.env.local not found!${NC}"
    echo "Please create this file with Firebase credentials. See docs/firebase-setup.md"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}ERROR: gcloud CLI not installed!${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "Setting GCP project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

echo -e "${GREEN}✓${NC} Pre-flight checks passed"
echo ""

##############################################################################
# STEP 1: Configuration Prompts
##############################################################################

echo -e "${YELLOW}[STEP 1]${NC} Gathering configuration..."

# Storage bucket name
read -p "Enter Cloud Storage bucket name (e.g., promote-autonomy-assets): " STORAGE_BUCKET
if [ -z "$STORAGE_BUCKET" ]; then
    echo -e "${RED}ERROR: Storage bucket name is required${NC}"
    exit 1
fi

# Generate or use existing Pub/Sub secret token
echo ""
echo "Generating Pub/Sub secret token..."
PUBSUB_SECRET=$(openssl rand -base64 32)
echo -e "${GREEN}✓${NC} Secret token generated: ${PUBSUB_SECRET:0:10}..."

echo ""
echo -e "${GREEN}✓${NC} Configuration complete"
echo ""

##############################################################################
# STEP 2: Enable Required APIs
##############################################################################

echo -e "${YELLOW}[STEP 2]${NC} Enabling required Google Cloud APIs..."

gcloud services enable run.googleapis.com \
    firestore.googleapis.com \
    pubsub.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    firebase.googleapis.com \
    --quiet

echo -e "${GREEN}✓${NC} APIs enabled"
echo ""

##############################################################################
# STEP 3: Create Service Accounts
##############################################################################

echo -e "${YELLOW}[STEP 3]${NC} Creating service accounts..."

# Strategy Agent Service Account
SA_STRATEGY="strategy-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $SA_STRATEGY &> /dev/null; then
    echo "  Strategy Agent SA already exists: $SA_STRATEGY"
else
    gcloud iam service-accounts create strategy-agent-sa \
        --display-name="Strategy Agent Service Account" \
        --quiet
    echo -e "${GREEN}  ✓${NC} Created Strategy Agent SA"
fi

# Grant roles to Strategy Agent SA
echo "  Granting IAM roles to Strategy Agent SA..."
for role in roles/datastore.user roles/pubsub.publisher roles/aiplatform.user roles/storage.objectCreator; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_STRATEGY" \
        --role="$role" \
        --condition=None \
        --quiet > /dev/null 2>&1 || true
done

# Creative Agent Service Account
SA_CREATIVE="creative-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $SA_CREATIVE &> /dev/null; then
    echo "  Creative Agent SA already exists: $SA_CREATIVE"
else
    gcloud iam service-accounts create creative-agent-sa \
        --display-name="Creative Agent Service Account" \
        --quiet
    echo -e "${GREEN}  ✓${NC} Created Creative Agent SA"
fi

# Grant roles to Creative Agent SA
echo "  Granting IAM roles to Creative Agent SA..."
for role in roles/datastore.user roles/storage.objectAdmin roles/aiplatform.user roles/pubsub.subscriber; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_CREATIVE" \
        --role="$role" \
        --condition=None \
        --quiet > /dev/null 2>&1 || true
done

# Pub/Sub Invoker Service Account
SA_INVOKER="pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $SA_INVOKER &> /dev/null; then
    echo "  Pub/Sub Invoker SA already exists: $SA_INVOKER"
else
    gcloud iam service-accounts create pubsub-invoker \
        --display-name="Pub/Sub Invoker for Creative Agent" \
        --quiet
    echo -e "${GREEN}  ✓${NC} Created Pub/Sub Invoker SA"
fi

echo -e "${GREEN}✓${NC} Service accounts configured"
echo ""

##############################################################################
# STEP 4: Create Cloud Storage Bucket
##############################################################################

echo -e "${YELLOW}[STEP 4]${NC} Creating Cloud Storage bucket..."

if gsutil ls -b gs://$STORAGE_BUCKET &> /dev/null; then
    echo "  Bucket already exists: gs://$STORAGE_BUCKET"
else
    gsutil mb -l $REGION gs://$STORAGE_BUCKET
    echo -e "${GREEN}  ✓${NC} Created bucket: gs://$STORAGE_BUCKET"
fi

echo -e "${GREEN}✓${NC} Storage bucket ready"
echo ""

##############################################################################
# STEP 5: Create Pub/Sub Topic
##############################################################################

echo -e "${YELLOW}[STEP 5]${NC} Creating Pub/Sub topic..."

PUBSUB_TOPIC="creative-tasks"
if gcloud pubsub topics describe $PUBSUB_TOPIC &> /dev/null; then
    echo "  Topic already exists: $PUBSUB_TOPIC"
else
    gcloud pubsub topics create $PUBSUB_TOPIC --quiet
    echo -e "${GREEN}  ✓${NC} Created topic: $PUBSUB_TOPIC"
fi

echo -e "${GREEN}✓${NC} Pub/Sub topic ready"
echo ""

##############################################################################
# STEP 5.5: Create Artifact Registry Repository
##############################################################################

echo -e "${YELLOW}[STEP 5.5]${NC} Creating Artifact Registry repository..."

ARTIFACT_REPO="cloud-run-source-deploy"
if gcloud artifacts repositories describe $ARTIFACT_REPO --location=$REGION &> /dev/null; then
    echo "  Repository already exists: $ARTIFACT_REPO"
else
    gcloud artifacts repositories create $ARTIFACT_REPO \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker repository for Cloud Run deployments" \
        --quiet
    echo -e "${GREEN}  ✓${NC} Created Artifact Registry repository: $ARTIFACT_REPO"
fi

echo -e "${GREEN}✓${NC} Artifact Registry ready"
echo ""

##############################################################################
# STEP 6: Deploy Strategy Agent
##############################################################################

echo -e "${YELLOW}[STEP 6]${NC} Deploying Strategy Agent to Cloud Run..."

# Placeholder for FRONTEND_URL (will update later)
FRONTEND_URL_PLACEHOLDER="https://placeholder-will-be-updated.run.app"

# Build container image from project root (includes shared package)
echo "  Building Strategy Agent container..."
gcloud builds submit \
    --config=cloudbuild-strategy.yaml \
    --region=$REGION \
    --substitutions=_REGION=$REGION \
    --quiet

# Deploy to Cloud Run
echo "  Deploying Strategy Agent to Cloud Run..."
gcloud run deploy strategy-agent \
    --image="$REGION-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/strategy-agent" \
    --region=$REGION \
    --service-account=$SA_STRATEGY \
    --set-env-vars=PROJECT_ID=$PROJECT_ID,\
LOCATION=$REGION,\
STORAGE_BUCKET=$STORAGE_BUCKET,\
GEMINI_MODEL=gemini-2.5-flash,\
PUBSUB_TOPIC=$PUBSUB_TOPIC,\
PUBSUB_SECRET_TOKEN=$PUBSUB_SECRET,\
USE_MOCK_GEMINI=false,\
USE_MOCK_FIRESTORE=false,\
USE_MOCK_PUBSUB=false,\
LOG_LEVEL=INFO,\
FRONTEND_URL=$FRONTEND_URL_PLACEHOLDER \
    --allow-unauthenticated \
    --max-instances=10 \
    --memory=512Mi \
    --timeout=60s \
    --quiet

# Get Strategy Agent URL
STRATEGY_AGENT_URL=$(gcloud run services describe strategy-agent --region=$REGION --format='value(status.url)')
echo -e "${GREEN}✓${NC} Strategy Agent deployed: $STRATEGY_AGENT_URL"

echo ""

##############################################################################
# STEP 7: Deploy Creative Agent
##############################################################################

echo -e "${YELLOW}[STEP 7]${NC} Deploying Creative Agent to Cloud Run..."

# Build container image from project root (includes shared package)
echo "  Building Creative Agent container..."
gcloud builds submit \
    --config=cloudbuild-creative.yaml \
    --region=$REGION \
    --substitutions=_REGION=$REGION \
    --quiet

# Deploy to Cloud Run
echo "  Deploying Creative Agent to Cloud Run..."
gcloud run deploy creative-agent \
    --image="$REGION-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/creative-agent" \
    --region=$REGION \
    --service-account=$SA_CREATIVE \
    --set-env-vars=PROJECT_ID=$PROJECT_ID,\
LOCATION=$REGION,\
STORAGE_BUCKET=$STORAGE_BUCKET,\
IMAGEN_MODEL=imagen-4.0-generate-001,\
VEO_MODEL=veo-3.0-generate-001,\
GEMINI_MODEL=gemini-2.5-flash,\
PUBSUB_SECRET_TOKEN=$PUBSUB_SECRET,\
USE_MOCK_GEMINI=false,\
USE_MOCK_IMAGEN=false,\
USE_MOCK_VEO=false,\
USE_MOCK_FIRESTORE=false,\
USE_MOCK_STORAGE=false,\
LOG_LEVEL=INFO,\
FRONTEND_URL=$FRONTEND_URL_PLACEHOLDER \
    --no-allow-unauthenticated \
    --max-instances=10 \
    --memory=2Gi \
    --timeout=300s \
    --quiet

# Get Creative Agent URL
CREATIVE_AGENT_URL=$(gcloud run services describe creative-agent --region=$REGION --format='value(status.url)')
echo -e "${GREEN}✓${NC} Creative Agent deployed: $CREATIVE_AGENT_URL"

# Grant Cloud Run Invoker role to Pub/Sub invoker SA
echo "  Granting Cloud Run Invoker permission..."
gcloud run services add-iam-policy-binding creative-agent \
    --region=$REGION \
    --member="serviceAccount:$SA_INVOKER" \
    --role="roles/run.invoker" \
    --quiet > /dev/null 2>&1

echo ""

##############################################################################
# STEP 8: Create Pub/Sub Push Subscription
##############################################################################

echo -e "${YELLOW}[STEP 8]${NC} Creating Pub/Sub push subscription..."

SUBSCRIPTION_NAME="creative-agent-sub"
if gcloud pubsub subscriptions describe $SUBSCRIPTION_NAME &> /dev/null; then
    echo "  Deleting existing subscription..."
    gcloud pubsub subscriptions delete $SUBSCRIPTION_NAME --quiet
fi

gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
    --topic=$PUBSUB_TOPIC \
    --push-endpoint="${CREATIVE_AGENT_URL}/api/consume" \
    --push-auth-service-account=$SA_INVOKER \
    --ack-deadline=300 \
    --quiet

echo -e "${GREEN}✓${NC} Pub/Sub subscription created"
echo ""

##############################################################################
# STEP 9: Deploy Frontend
##############################################################################

echo -e "${YELLOW}[STEP 9]${NC} Deploying Frontend to Cloud Run..."

# Read Firebase config from .env.local
FIREBASE_API_KEY=$(grep NEXT_PUBLIC_FIREBASE_API_KEY frontend/.env.local | cut -d '=' -f2)
FIREBASE_AUTH_DOMAIN=$(grep NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN frontend/.env.local | cut -d '=' -f2)
FIREBASE_PROJECT_ID=$(grep NEXT_PUBLIC_FIREBASE_PROJECT_ID frontend/.env.local | cut -d '=' -f2)
FIREBASE_STORAGE_BUCKET=$(grep NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET frontend/.env.local | cut -d '=' -f2)
FIREBASE_MESSAGING_SENDER_ID=$(grep NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID frontend/.env.local | cut -d '=' -f2)
FIREBASE_APP_ID=$(grep NEXT_PUBLIC_FIREBASE_APP_ID frontend/.env.local | cut -d '=' -f2)

gcloud run deploy frontend \
    --source=frontend \
    --region=$REGION \
    --platform=managed \
    --set-env-vars=NEXT_PUBLIC_FIREBASE_API_KEY=$FIREBASE_API_KEY,\
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=$FIREBASE_AUTH_DOMAIN,\
NEXT_PUBLIC_FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID,\
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=$FIREBASE_STORAGE_BUCKET,\
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=$FIREBASE_MESSAGING_SENDER_ID,\
NEXT_PUBLIC_FIREBASE_APP_ID=$FIREBASE_APP_ID,\
NEXT_PUBLIC_STRATEGY_AGENT_URL=$STRATEGY_AGENT_URL \
    --allow-unauthenticated \
    --max-instances=10 \
    --memory=512Mi \
    --timeout=60s \
    --quiet

# Get Frontend URL
FRONTEND_URL=$(gcloud run services describe frontend --region=$REGION --format='value(status.url)')
echo -e "${GREEN}✓${NC} Frontend deployed: $FRONTEND_URL"

echo ""

##############################################################################
# STEP 10: Update Backend Services with Frontend URL
##############################################################################

echo -e "${YELLOW}[STEP 10]${NC} Updating backend services with frontend URL..."

# Update Strategy Agent
echo "  Updating Strategy Agent CORS..."
gcloud run services update strategy-agent \
    --region=$REGION \
    --update-env-vars=FRONTEND_URL=$FRONTEND_URL \
    --quiet

# Update Creative Agent
echo "  Updating Creative Agent CORS..."
gcloud run services update creative-agent \
    --region=$REGION \
    --update-env-vars=FRONTEND_URL=$FRONTEND_URL \
    --quiet

echo -e "${GREEN}✓${NC} Backend services updated"
echo ""

##############################################################################
# STEP 11: Summary & Next Steps
##############################################################################

echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Deployment Complete! 🎉${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Service URLs:"
echo "  Frontend:        $FRONTEND_URL"
echo "  Strategy Agent:  $STRATEGY_AGENT_URL"
echo "  Creative Agent:  $CREATIVE_AGENT_URL"
echo ""
echo "Configuration:"
echo "  Project ID:      $PROJECT_ID"
echo "  Region:          $REGION"
echo "  Storage Bucket:  gs://$STORAGE_BUCKET"
echo "  Pub/Sub Topic:   $PUBSUB_TOPIC"
echo ""
echo -e "${YELLOW}IMPORTANT: Complete these manual steps:${NC}"
echo ""
echo "1. Add Frontend URL to Firebase Authorized Domains:"
echo "   - Go to: https://console.firebase.google.com/project/$PROJECT_ID/authentication/settings"
echo "   - Navigate to 'Authorized domains' tab"
echo "   - Add: $(echo $FRONTEND_URL | sed 's/https:\/\///')"
echo ""
echo "2. Test the deployment:"
echo "   - Visit: $FRONTEND_URL"
echo "   - Sign in with Google"
echo "   - Submit a test marketing goal"
echo "   - Approve the generated plan"
echo "   - Wait for asset generation (~30-60 seconds)"
echo ""
echo "3. Monitor logs:"
echo "   - Strategy Agent: gcloud run services logs read strategy-agent --region=$REGION"
echo "   - Creative Agent: gcloud run services logs read creative-agent --region=$REGION"
echo "   - Frontend:       gcloud run services logs read frontend --region=$REGION"
echo ""
echo -e "${GREEN}Your hackathon demo is ready! 🚀${NC}"
echo ""

# Save deployment info to file
cat > deployment-info.txt <<EOF
Promote Autonomy - Deployment Information
Generated: $(date)

Service URLs:
  Frontend:        $FRONTEND_URL
  Strategy Agent:  $STRATEGY_AGENT_URL
  Creative Agent:  $CREATIVE_AGENT_URL

Configuration:
  Project ID:      $PROJECT_ID
  Region:          $REGION
  Storage Bucket:  gs://$STORAGE_BUCKET
  Pub/Sub Topic:   $PUBSUB_TOPIC
  Pub/Sub Secret:  $PUBSUB_SECRET

Service Accounts:
  Strategy Agent:  $SA_STRATEGY
  Creative Agent:  $SA_CREATIVE
  Pub/Sub Invoker: $SA_INVOKER

Next Steps:
1. Add frontend domain to Firebase authorized domains
2. Test end-to-end workflow
3. Submit hackathon entry with Frontend URL
EOF

echo "Deployment info saved to: deployment-info.txt"
echo ""
