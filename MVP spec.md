# Promote Autonomy: AI-Driven Marketing Automation MVP Specification (HITL Edition)

## 1. Overview
Promote Autonomy is a cloud-based multi-agent system designed to automate marketing and promotional content creation for startups and individual creators. The system integrates AI-driven strategy generation with **Human-in-the-Loop (HITL)** approval to ensure safe, realistic, and production-ready workflows.

Users provide a high-level marketing goal, the Strategy Agent generates a structured promotional plan, and *only after explicit human approval* does the Creative Agent begin producing assets such as copy, images, and optional video content.

The architecture is built on Google Cloud Run, Pub/Sub, Firebase, Vertex AI (Gemini / Imagen / Veo), and Firestore.

---

## 2. Architecture Components
Promote Autonomy consists of three Cloud Run services, Firebase Authentication, Firestore, and Cloud Storage.

### 1. Frontend (Next.js / Cloud Run Service)
- Provides login, goal input, and approval UI
- Monitors Firestore documents in `jobs/{event_id}` in real time
- Displays AI-generated promotional plans awaiting user approval
- Sends approval actions to the Strategy Agent via an API call (client never writes Firestore directly)

### 2. Strategy Agent (Cloud Run Service)
- Receives marketing goals from the Frontend
- Uses Gemini to generate a structured task list
- Saves the proposal into Firestore with `status = "pending_approval"`
- Exposes an `/approve` API:
  - Validates Firebase ID Token
  - Uses a Firestore transaction to update `pending_approval → processing`
  - Publishes the task list to Pub/Sub **only once** (idempotent)

### 3. Creative Agent (Cloud Run Service / Pub/Sub Push Consumer)
- Triggered by Pub/Sub messages after user approval
- Generates copy, images, and optional video assets
- Uploads assets to Cloud Storage
- Updates Firestore `jobs/{event_id}` with `status = "completed"` and output URLs
- Independent of HITL logic and requires no modification

### 4. Firebase Authentication
- Supports Google login or email-based authentication
- ID Tokens are verified by the Strategy Agent for access control

### 5. Firestore
Central job state management:
```
/jobs/{event_id}
  uid
  task_list
  status: pending_approval | approved | processing | completed | failed | rejected
  approved_at
  createdAt / updatedAt
  captions[] / images[] / videos[] / posts{}
  audit_logs[] (optional)
```
Client can **read only**. All state mutations are server-side.

### 6. Cloud Storage
- Stores images, videos, and other generated assets
- Organized per job: `event_id/asset.png`

---

## 3. Data Flow (HITL Workflow)
1. **Frontend → Strategy Agent**: User submits a marketing goal
2. **Strategy Agent** generates a task list and saves it as `pending_approval` in Firestore
3. **Frontend** displays the plan and asks for user approval
4. **Frontend → Strategy Agent `/approve`**: On approval, sends event_id with ID Token
5. **Strategy Agent**:
   - Firestore transaction moves `pending_approval → processing`
   - Publishes the task list to Pub/Sub
6. **Creative Agent** executes tasks and uploads generated content
7. **Creative Agent → Firestore**: Sets `status = completed`
8. **Frontend** renders the final asset dashboard

---

## 4. Task List Schema
```json
{
  "event_id": "01JD4S3ABC...",
  "uid": "user123",
  "task_list": {
    "goal": "Increase awareness of new feature",
    "tasks": {
      "captions": { "n": 3, "style": "twitter" },
      "image": { "prompt": "Clean blue modern promo visual", "size": "square" },
      "video": { "prompt": "10s product trailer", "durationSec": 10 }
    }
  },
  "created_at": 1731030000
}
```

---

## 5. Implementation Steps (HITL-Compatible)
### STEP 1. Cloud Setup
1. Create Firebase project (Auth + Firestore)
2. Create Cloud Storage bucket
3. Create Pub/Sub topic (`autonomy-tasks`)
4. Create separate service accounts for frontend, strategy, creative
5. Apply Firestore security rules (client read-only)
6. Assign minimal IAM roles

### STEP 2. Frontend
1. Google login using Firebase Auth
2. Submit goal → receive event_id
3. Listen for Firestore updates
4. If `pending_approval`, show approval UI
5. Call Strategy Agent `/approve` API with ID Token
6. Render processing → completed states

### STEP 3. Strategy Agent
#### `/strategize`
- Generate task list via Gemini
- Save as Firestore document with `status = pending_approval`

#### `/approve`
- Validate ID Token
- Firestore transaction:
  - Only allow transition `pending_approval → processing`
  - Stamp `approved_at`
- Publish to Pub/Sub after successful transition
- Log approval (optional)

### STEP 4. Creative Agent
- Receive Pub/Sub message
- Generate copy / image / video
- Upload to Storage
- Update Firestore with `completed`

### STEP 5. Firestore & Storage Model
**Firestore**
```
/jobs/{event_id}
  task_list
  status
  approved_at
  outputs{}
  audit_logs[]
```
**Storage**
```
/event_id/image.png
/event_id/video.mp4
```

---

## 6. Fallback Logic
- If Imagen unavailable → generate placeholder PNG
- If Veo unavailable → generate script-only video brief
- If quota exceeded → text-only outputs
- Failures set `status = failed` and log error

---

## 7. Demo Flow (Optimized for HITL)
1. User inputs goal
2. AI generates strategy → shown as pending approval
3. User reviews and approves
4. Creative Agent begins processing
5. Final assets appear (copy, image, video or script)
6. One-click copy to social media draft

---

## 8. Future Enhancements
- Pre-approval lightweight editing (copy tweaks, NG-word checks)
- Brand Style Guide integration
- A/B variants and comparative approval
- Multi-role workflows (editor vs approver)
- Feedback loop based on social performance

---

## 9. Conclusion
Promote Autonomy is now a complete HITL-enabled, production-realistic multi-agent marketing automation system. It provides:

### ✅ Real-world-safe workflows
### ✅ Clean architectural boundaries
### ✅ Hackathon-ready clarity and polish

With this specification, you can confidently begin implementing the system in GitHub.

