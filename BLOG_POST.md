# Building a Multi-Agent Marketing System with Google ADK and Cloud Run

*How I built an AI-powered marketing automation platform with human oversight using Google's Agent Development Kit*

---

## The Challenge: AI Needs Human Oversight

We've all seen the promise of AI-generated content. Marketing teams everywhere are experimenting with tools that can write social media captions, generate images, and even create videos. But there's a critical problem: **AI makes mistakes**.

A fully automated marketing system might:
- Generate off-brand content
- Create inappropriate imagery
- Misunderstand campaign goals
- Waste budget on poor-quality assets

The solution? **Human-in-the-Loop (HITL)** — AI generates the content, but humans approve before execution.

For the Cloud Run Hackathon, I built **Promote Autonomy**: a multi-agent marketing automation system that combines Google's Agent Development Kit (ADK) with a mandatory human approval workflow, all deployed on Cloud Run.

**Try the live demo**: https://frontend-909635873035.asia-northeast1.run.app

---

## Architecture Overview: Three Services, One Workflow

The system is built on three independent Cloud Run services that communicate asynchronously via Pub/Sub:

### 1. Frontend (Next.js)
- User-facing web interface for goal submission
- Real-time job status updates via Firestore listeners
- Approval/rejection workflow for generated plans
- Display of final assets (captions, images, videos)

### 2. Strategy Agent (FastAPI + Gemini)
- Receives marketing goals from users
- Uses Gemini 2.5 Flash to generate comprehensive marketing plans
- Saves plans to Firestore with `status = pending_approval`
- **Critical HITL step**: Only publishes to Pub/Sub after human approval
- Implements atomic Firestore transactions to prevent race conditions

### 3. Creative Agent (FastAPI + ADK)
- Receives approved tasks via Pub/Sub push subscription
- **ADK Multi-Agent Coordinator** orchestrates three specialized sub-agents:
  - **Copy Writer Agent**: Generates social media captions using Gemini
  - **Image Creator Agent**: Generates promotional images using Imagen 4.0
  - **Video Producer Agent**: Generates promotional videos using Veo 3.0
- All three agents execute in parallel for efficiency
- Results uploaded to Cloud Storage with public URLs

### The Data Flow

```
User → Frontend → Strategy Agent → Gemini → Firestore (pending_approval)
                                                ↓
User reviews plan → Approves → Firestore transaction + Pub/Sub publish
                                                ↓
Creative Agent ← Pub/Sub ← ADK Coordinator delegates to 3 sub-agents
                                                ↓
Gemini (captions) + Imagen (images) + Veo (videos) → Cloud Storage
                                                ↓
Firestore (completed) → Frontend displays assets
```

**Key Innovation**: The atomic Firestore transaction ensures that approval state and Pub/Sub message publishing happen together — preventing duplicate executions or lost messages.

---

## Why Google ADK? The Multi-Agent Orchestration Problem

Initially, I orchestrated the three asset generation tasks using basic `asyncio.gather()`:

```python
# Original approach: Manual orchestration
captions_url, image_url, video_url = await asyncio.gather(
    generate_captions_task(),
    generate_image_task(),
    generate_video_task(),
)
```

This worked, but had limitations:
- No built-in retry logic
- Manual error handling for each task
- Hard to add new agents or modify workflow
- Difficult to test individual agent behavior

### Enter Google ADK

Google's Agent Development Kit (ADK) provides a framework for building multi-agent systems with **automatic orchestration**. Here's how I restructured the Creative Agent:

#### 1. Define Tools as Regular Functions

ADK automatically wraps Python functions as tools for agents:

```python
# creative-agent/app/agents/tools.py

async def generate_captions_tool(
    config: dict[str, Any],
    goal: str,
    event_id: str
) -> dict[str, str]:
    """Generate social media captions using Gemini and upload to Cloud Storage.

    Args:
        config: Caption configuration (n, style)
        goal: Marketing goal for context
        event_id: Job ID for storage path

    Returns:
        Dict with captions_url key
    """
    caption_config = CaptionTaskConfig(**config)
    copy_service = get_copy_service()
    storage_service = get_storage_service()

    # Generate captions
    captions = await copy_service.generate_captions(caption_config, goal)

    # Upload to storage
    captions_json = json.dumps(captions, indent=2).encode("utf-8")
    url = await storage_service.upload_file(
        event_id=event_id,
        filename="captions.json",
        content=captions_json,
        content_type="application/json",
    )

    return {"captions_url": url}
```

**No decorators needed** — ADK inspects function signatures, docstrings, and type hints to automatically generate tool schemas for the LLM.

#### 2. Create Specialized Sub-Agents

Each sub-agent is an `LlmAgent` with a specific role and tools:

```python
# creative-agent/app/agents/coordinator.py

def create_copy_agent() -> LlmAgent:
    """Create ADK agent for caption generation."""
    return LlmAgent(
        name="copy_writer",
        model="gemini-2.5-flash",
        instruction="""You are a creative copywriter specialized in social media captions.
        Generate engaging, on-brand captions that match the requested style.
        Always call the generate_captions_tool to create captions.""",
        description="Generates social media captions using Gemini",
        tools=[generate_captions_tool],
    )

def create_image_agent() -> LlmAgent:
    """Create ADK agent for image generation."""
    return LlmAgent(
        name="image_creator",
        model="gemini-2.5-flash",
        instruction="""You are a visual designer specialized in promotional graphics.
        Generate images that match the requested prompt, size, and aspect ratio.
        Always call the generate_image_tool to create images.""",
        description="Generates promotional images using Imagen",
        tools=[generate_image_tool],
    )

def create_video_agent() -> LlmAgent:
    """Create ADK agent for video generation."""
    return LlmAgent(
        name="video_producer",
        model="gemini-2.5-flash",
        instruction="""You are a video producer specialized in short-form promotional videos.
        Generate videos that match the requested prompt, duration, and aspect ratio.
        Always call the generate_video_tool to create videos.""",
        description="Generates promotional videos using Veo",
        tools=[generate_video_tool],
    )
```

#### 3. Create the Coordinator Agent

The coordinator delegates tasks to the specialized sub-agents:

```python
def create_creative_coordinator() -> LlmAgent:
    """Create ADK coordinator agent that orchestrates all creative agents."""
    copy_agent = create_copy_agent()
    image_agent = create_image_agent()
    video_agent = create_video_agent()

    coordinator = LlmAgent(
        name="creative_director",
        model="gemini-2.5-flash",
        instruction="""You are a creative director coordinating asset generation.

        Your job is to delegate tasks to specialized agents:
        - copy_writer: For captions
        - image_creator: For images
        - video_producer: For videos

        Delegate ALL tasks in parallel for efficiency.
        Collect all results and return them in a structured format.

        If any agent fails, continue with others and report the error.""",
        description="Coordinates creative asset generation across multiple specialized agents",
        sub_agents=[copy_agent, image_agent, video_agent],
    )

    return coordinator
```

#### 4. Run the Coordinator

Using ADK's `Runner` API to execute the multi-agent workflow:

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def generate_assets_with_adk(event_id: str, task_list: TaskList) -> dict:
    """Generate assets using ADK multi-agent orchestration."""
    coordinator = get_creative_coordinator()

    # Prepare prompt for coordinator
    prompt = f"""Generate creative assets for this marketing campaign:

Goal: {task_list.goal}
Target Platforms: {', '.join(p.value for p in task_list.target_platforms)}
Event ID: {event_id}

Tasks to complete:
{json.dumps(task_list.tasks, indent=2)}

Delegate each task to the appropriate specialized agent.
Run all tasks in parallel for efficiency.
Return URLs for all generated assets."""

    # Run ADK coordinator
    session_service = InMemorySessionService()
    runner = Runner(
        agent=coordinator,
        app_name="creative-agent",
        session_service=session_service
    )

    user_message = types.Content(
        role='user',
        parts=[types.Part(text=prompt)]
    )

    # Execute and collect results
    def run_agent():
        events = runner.run(
            user_id="creative-agent",
            session_id=event_id,
            new_message=user_message
        )
        for event in events:
            if event.is_final_response() and event.content:
                return event.content.parts[0].text
        return ""

    result = await asyncio.to_thread(run_agent)

    # Parse URLs from response
    return {
        "captions_url": extract_url(result, "captions"),
        "image_url": extract_url(result, "image"),
        "video_url": extract_url(result, "video"),
    }
```

### Benefits of ADK Orchestration

1. **Automatic Parallel Execution**: ADK handles running sub-agents concurrently
2. **Built-in Error Handling**: Coordinator can decide how to handle failures
3. **Extensible**: Easy to add new agents (e.g., brand style guide checker)
4. **Testable**: Can test each agent independently
5. **Observability**: ADK provides logging and tracing out of the box

---

## Technical Challenges & Solutions

### Challenge 1: Atomic HITL Approval

**Problem**: The approval workflow required updating Firestore state AND publishing to Pub/Sub. If either operation failed, the system would be in an inconsistent state.

**Solution**: Firestore transactions with conditional updates:

```python
# strategy-agent/app/routers/approve.py

@router.post("/approve")
async def approve_strategy(request: ApproveRequest):
    """Approve pending strategy with atomic state transition."""
    firestore_service = get_firestore_service()
    pubsub_service = get_pubsub_service()

    # Atomic transaction: only update if status is pending_approval
    @firestore.transactional
    def update_in_transaction(transaction, job_ref):
        snapshot = job_ref.get(transaction=transaction)

        if not snapshot.exists:
            raise HTTPException(status_code=404, detail="Job not found")

        job = snapshot.to_dict()

        # Conditional update: only proceed if pending approval
        if job["status"] != "pending_approval":
            raise HTTPException(
                status_code=409,
                detail=f"Job already {job['status']}"
            )

        # Update status to processing
        transaction.update(job_ref, {
            "status": "processing",
            "approved_at": firestore.SERVER_TIMESTAMP,
        })

    # Execute transaction
    job_ref = firestore_service.db.collection("jobs").document(event_id)
    transaction = firestore_service.db.transaction()
    update_in_transaction(transaction, job_ref)

    # Only publish to Pub/Sub after successful transaction
    await pubsub_service.publish_task(event_id, task_list)

    return {"status": "approved", "event_id": event_id}
```

**Key Insight**: The transaction prevents duplicate approvals, and we only publish to Pub/Sub **after** the transaction succeeds. This ensures exactly-once approval semantics.

### Challenge 2: Long-Running AI Models

**Problem**: Veo video generation can take 2-5 minutes. Without proper timeout handling, requests would hang indefinitely.

**Solution**: Layered timeout protection:

```python
# creative-agent/app/services/video.py

async def generate_video(self, task: VideoTaskConfig) -> bytes:
    """Generate video with timeout protection."""
    try:
        # Timeout at service level (120 seconds)
        video_bytes = await asyncio.wait_for(
            asyncio.to_thread(self._generate_video_sync, task),
            timeout=self.settings.VEO_TIMEOUT_SEC
        )
        return video_bytes
    except asyncio.TimeoutError:
        logger.error(f"Veo generation timed out after {self.settings.VEO_TIMEOUT_SEC}s")
        raise HTTPException(status_code=504, detail="Video generation timed out")
```

Additionally, Cloud Run services have request timeouts (default 5 minutes), providing another layer of protection.

### Challenge 3: ADK Runner is Synchronous

**Problem**: ADK's `Runner.run()` is a synchronous generator, but our FastAPI app is async.

**Solution**: Use `asyncio.to_thread()` to run the synchronous ADK code in a thread pool:

```python
def run_agent():
    events = runner.run(
        user_id="creative-agent",
        session_id=event_id,
        new_message=user_message
    )
    for event in events:
        if event.is_final_response() and event.content:
            return event.content.parts[0].text
    return ""

result = await asyncio.to_thread(run_agent)
```

This prevents blocking the async event loop while maintaining compatibility with FastAPI.

### Challenge 4: Pub/Sub Authentication

**Problem**: The Creative Agent's `/consume` endpoint needs to verify that incoming requests actually come from Pub/Sub (not malicious actors).

**Solution**: OIDC token verification:

```python
# creative-agent/app/routers/consume.py

@router.post("/consume")
async def consume_task(
    pubsub_message: PubSubMessage,
    request: Request,
    authorization: str | None = Header(None),
):
    """Consume task from Pub/Sub with OIDC authentication."""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")

    # Verify OIDC token from Pub/Sub
    try:
        token = authorization.split("Bearer ")[1]
        audience = str(request.url)

        # Verify token with Google's token verification
        id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=audience
        )
    except Exception as e:
        logger.error(f"OIDC verification failed: {e}")
        raise HTTPException(status_code=403, detail="Invalid token")

    # Token verified - process message
    # ...
```

The Pub/Sub subscription is configured with a service account that has permission to invoke the Cloud Run service, and Pub/Sub automatically includes an OIDC token in the `Authorization` header.

---

## Results & Learnings

### What Works Well

**End-to-End Workflow**: The full pipeline (goal submission → plan generation → human approval → asset creation → display) completes in 60-120 seconds for a typical job.

**ADK Integration**: The multi-agent coordinator makes the Creative Agent significantly more maintainable. Adding a new agent type (e.g., brand compliance checker) would take ~30 minutes.

**Real-Time Updates**: Firestore listeners provide instant feedback to users as job status changes, creating a responsive UX without polling.

**Production Ready**: 83 passing tests, full CI/CD pipeline, comprehensive error handling, and security hardening (Firebase Auth, OIDC, Firestore security rules).

### Performance Metrics

- **Strategy Generation**: 3-10 seconds (Gemini API call)
- **Caption Generation**: 5-15 seconds (Gemini API call)
- **Image Generation**: 20-40 seconds (Imagen 4.0)
- **Video Generation**: 2-5 minutes (Veo 3.0 is slow but produces high-quality results)
- **Total Workflow**: 60-120 seconds for captions + image, 3-7 minutes with video

### Key Learnings

1. **ADK Coordinator Pattern is Powerful**: Separating orchestration logic (coordinator) from execution logic (tools) makes the system extensible and testable.

2. **Atomic Transactions are Critical**: In distributed systems, ensuring state consistency requires careful use of transactions. Firestore transactions prevented race conditions in the approval workflow.

3. **Async/Sync Bridging**: Integrating synchronous libraries (ADK) with async frameworks (FastAPI) requires `asyncio.to_thread()` or similar patterns.

4. **HITL is Non-Negotiable**: Every test run where I skipped the approval step generated at least one piece of content I wouldn't want published. Human oversight is essential for AI-generated marketing.

5. **Cloud Run is Perfect for AI Workloads**: Auto-scaling handles variable AI model latency (Imagen takes 30s, Veo takes 3 minutes). Pay-per-use pricing means we only pay when jobs are running.

---

## Future Enhancements

The current system is an MVP, but there are several natural next steps:

### 1. Multi-Modal Input (Product Photos)
Currently, users describe products in text. Next version will support uploading product photos that Gemini analyzes for visual context, ensuring generated images match the actual product.

### 2. Platform-Specific Configuration
Generate assets tailored to each platform:
- Instagram: 1:1 square images, 15-second videos
- X (Twitter): 16:9 images, 2:20 max videos
- LinkedIn: 1.91:1 images, professional tone

### 3. Brand Style Guide Integration
Add a fourth agent (brand guardian) that validates all generated content against uploaded brand guidelines (colors, fonts, tone, taglines).

### 4. Performance Feedback Loop
Track which generated assets perform well (likes, shares, conversions) and feed this data back to improve future generations.

---

## Try It Yourself

**Live Demo**: https://frontend-909635873035.asia-northeast1.run.app
**Source Code**: https://github.com/TheIllusionOfLife/promote_autonomy
**Architecture Diagram**: [View on GitHub](https://github.com/TheIllusionOfLife/promote_autonomy/blob/main/architecture-diagram.svg)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/TheIllusionOfLife/promote_autonomy.git
cd promote_autonomy

# Install shared schemas
cd shared && uv sync

# Set up Strategy Agent
cd ../strategy-agent
cp .env.example .env
# Edit .env with your Google Cloud credentials
uv sync
uv run pytest  # Run tests

# Set up Creative Agent
cd ../creative-agent
cp .env.example .env
# Edit .env with your credentials
uv sync
uv run pytest  # Run tests

# Set up Frontend
cd ../frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with Firebase config
npm run dev
```

The system supports **mock mode** for rapid development without API costs:
- `USE_MOCK_GEMINI=true` (no Gemini API calls)
- `USE_MOCK_IMAGEN=true` (placeholder images)
- `USE_MOCK_VEO=true` (text briefs only)

---

## Conclusion

Building Promote Autonomy taught me that **multi-agent systems are the future of AI applications**. Rather than building monolithic AI systems, we can compose specialized agents that work together, each focused on one task.

Google's ADK makes this pattern accessible. The coordinator pattern, automatic tool wrapping, and built-in orchestration eliminate much of the boilerplate code required for multi-agent systems.

Cloud Run provides the perfect deployment platform: auto-scaling handles variable AI workload patterns, independent service deployment enables microservices architecture, and pay-per-use pricing keeps costs low during development.

Most importantly, the Human-in-the-Loop approval workflow demonstrates that **AI augmentation beats AI automation**. Rather than replacing human marketers, this system makes them more productive by handling the repetitive work while keeping humans in control of strategy and quality.

If you're building AI applications, consider:
1. **Break complex tasks into specialized agents** (coordinator pattern)
2. **Use ADK for orchestration** (handles parallel execution, error handling, observability)
3. **Deploy on Cloud Run** (serverless, auto-scaling, cost-effective)
4. **Keep humans in the loop** (AI generates, humans approve)

---

**About the Hackathon**

*This content was created for the purposes of entering the Cloud Run Hackathon in the AI Agents category. The hackathon challenges developers to build innovative applications using Cloud Run and Google's Agent Development Kit (ADK). Promote Autonomy demonstrates how multi-agent systems can solve real-world problems while maintaining human oversight.*

**Technology Stack**: Google ADK, Cloud Run, Gemini 2.5 Flash, Imagen 4.0, Veo 3.0, Firestore, Pub/Sub, Cloud Storage, Next.js, FastAPI, Python 3.11+

---

*Have questions about the implementation? Want to contribute? Find me on GitHub or check out the live demo!*
