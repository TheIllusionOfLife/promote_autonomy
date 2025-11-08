# Promote Autonomy – Milestone Roadmap
This roadmap focuses on delivering a stable, scalable, and user-friendly HITL-based marketing automation system.

---

## Milestone 1 — Core MVP (Weeks 1–2)
**Goal:** Deliver a fully functional HITL-enabled prototype.

### Deliverables
- Frontend: login, goal input, approval UI, dashboard
- Strategy Agent: /strategize + /approve
- Creative Agent: Pub/Sub worker
- Firestore schema and security rules
- Placeholder asset generation (Imagen/Veo optional)

### Success Criteria
- End-to-end workflow functional
- At least one image + copy generated reliably
- HITL approval flow stable and auditable

---

## Milestone 2 — Production Stability (Weeks 3–5)
**Goal:** Improve robustness, reliability, and developer experience.

### Deliverables
- Idempotent approval logic
- Improved error handling & logging
- Retry handling for Pub/Sub deliveries
- Signed URLs for Storage assets
- System-wide monitoring (Logging, Error Reporting)

### Success Criteria
- Zero duplicate asset executions
- Clear audit trail for each job
- No unhandled exceptions in logs

---

## Milestone 3 — Enhanced AI Generation (Weeks 5–7)
**Goal:** Increase quality and customization of generated marketing output.

### Deliverables
- Imagen integration for high-quality images
- Veo (optional) short video generation
- Style profiles (Brand Style Guide)
- Social post auto-drafting (Twitter/X, LinkedIn)

### Success Criteria
- User-perceived quality improvement
- Brand-consistent outputs on repeated runs

---

## Milestone 4 — Collaboration & Team Features (Weeks 7–10)
**Goal:** Enable multi-user business workflows.

### Deliverables
- Role-based access (editor vs approver)
- Shared team workspace
- Approval history with comments
- Multi-tenant Firestore structure

### Success Criteria
- Teams can jointly manage promotional campaigns
- Full traceability of approval actions

---

## Milestone 5 — Intelligent Feedback Loop (Weeks 10–14)
**Goal:** Add performance-aware iteration.

### Deliverables
- Social performance hooks (clicks, impressions via external integrations)
- Feedback-driven re-generation suggestions
- Basic analytics dashboard

### Success Criteria
- Regeneration improves quality metrics
- Meaningful insights for users

---

## Long-Term Vision
- Autonomous multi-step marketing agents
- Cross-platform publishing (multi-channel)
- Full campaign simulation and forecasting
