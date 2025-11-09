# Firebase Setup Guide

This guide walks you through setting up Firebase for the Promote Autonomy project. You'll complete this BEFORE running the automated deployment script.

**Estimated Time**: 10-15 minutes

---

## Prerequisites

- Google Cloud Project ID: `promote-autonomy`
- Firebase CLI installed (`npm install -g firebase-tools`)
- Logged in to Firebase CLI (`firebase login`)

---

## Step 1: Initialize Firebase in Your Project

```bash
cd /Users/yuyamukai/dev/promote_autonomy

# Initialize Firebase (select Firestore only)
firebase init

# When prompted, select:
# - Firestore: Configure security rules and indexes files
# - Use existing project: promote-autonomy
# - Firestore rules file: firestore.rules (already exists, press Enter)
# - Firestore indexes file: firestore.indexes.json (press Enter for default)
```

This creates a `.firebaserc` file linking your local project to the Firebase project.

---

## Step 2: Enable Firebase Authentication

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **promote-autonomy**
3. Navigate to **Build** → **Authentication**
4. Click **Get Started**
5. Select **Google** sign-in provider
6. Enable the toggle
7. Enter support email (your email)
8. Click **Save**

---

## Step 3: Get Firebase Configuration for Frontend

1. In Firebase Console, click the **gear icon** (Project settings) near "Project Overview"
2. Scroll down to **Your apps** section
3. Click the **</>** (Web) icon to add a web app
4. App nickname: `promote-autonomy-frontend`
5. **Do NOT** check "Also set up Firebase Hosting"
6. Click **Register app**
7. Copy the `firebaseConfig` object shown

It will look like:
```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "promote-autonomy.firebaseapp.com",
  projectId: "promote-autonomy",
  storageBucket: "promote-autonomy.firebasestorage.app",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

---

## Step 4: Create Frontend Environment File

Create `/Users/yuyamukai/dev/promote_autonomy/frontend/.env.local` with the values from Step 3:

```bash
# Firebase Configuration (from Firebase Console)
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSy...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=promote-autonomy.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=promote-autonomy
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=promote-autonomy.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abc123

# Strategy Agent API (placeholder - will be updated after deployment)
NEXT_PUBLIC_STRATEGY_AGENT_URL=https://placeholder-will-be-updated
```

**Important**: The `NEXT_PUBLIC_STRATEGY_AGENT_URL` will be updated after you deploy the Strategy Agent.

---

## Step 5: Deploy Firestore Security Rules

```bash
cd /Users/yuyamukai/dev/promote_autonomy

# Deploy the existing security rules
firebase deploy --only firestore:rules

# You should see:
# ✔  firestore: released rules firestore.rules to cloud.firestore
```

---

## Step 6: Add Authorized Domains (After Deployment)

After deploying your frontend, you'll need to add its domain to Firebase authorized domains:

1. Go to Firebase Console → **Authentication** → **Settings** tab
2. Scroll to **Authorized domains**
3. Click **Add domain**
4. Add your Cloud Run frontend URL (e.g., `promote-autonomy-frontend-xxx.run.app`)

**Note**: You'll complete this step AFTER running the deployment script.

---

## Verification Checklist

Before proceeding to deployment, verify:

- [ ] `.firebaserc` file exists in project root
- [ ] `firebase deploy --only firestore:rules` succeeded
- [ ] `frontend/.env.local` file created with all Firebase config values
- [ ] Google sign-in provider enabled in Firebase Console
- [ ] You have the Firebase API key and other credentials ready

---

## Troubleshooting

### Error: "No Firebase project found"
Run `firebase init` again and select your existing project.

### Error: "Permission denied on Firestore rules"
Ensure you're logged in with the correct Google account that owns the project:
```bash
firebase login --reauth
```

### Can't find Firebase config
Go to Project Settings → General → Your apps → Web app → SDK setup and configuration

---

## Next Steps

After completing this guide, you're ready to run the automated deployment script:

```bash
./deploy.sh
```

The script will use the Firebase configuration you've set up and deploy all services to Cloud Run.
