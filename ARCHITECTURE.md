# Promote Autonomy - Architecture Diagram

## System Architecture Overview

```mermaid
graph TB
    subgraph "User Interface"
        UI[Frontend<br/>Next.js on Cloud Run<br/>Port 3000]
    end

    subgraph "Strategy Layer"
        SA[Strategy Agent<br/>FastAPI on Cloud Run<br/>Port 8000]
        SAG[Gemini 2.5 Flash<br/>Task Planning]
    end

    subgraph "Creative Layer - ADK Multi-Agent System"
        CA[Creative Agent<br/>FastAPI on Cloud Run<br/>Port 8001]

        subgraph "ADK Coordinator"
            COORD[Creative Director<br/>LlmAgent Coordinator<br/>Gemini 2.5 Flash]

            subgraph "Specialized Sub-Agents"
                COPY[Copy Writer Agent<br/>Caption Generation]
                IMG[Image Creator Agent<br/>Image Generation]
                VID[Video Producer Agent<br/>Video Generation]
            end
        end

        subgraph "Vertex AI Services"
            GEM[Gemini 2.5 Flash<br/>Copy Generation]
            IMAGEN[Imagen 4.0<br/>Image Generation]
            VEO[Veo 3.0<br/>Video Generation]
        end
    end

    subgraph "Data Layer"
        FS[(Firestore<br/>State Management)]
        PS[Pub/Sub Topic<br/>creative-tasks]
        CS[Cloud Storage<br/>Generated Assets]
    end

    subgraph "Authentication"
        AUTH[Firebase Auth<br/>Anonymous Users]
    end

    %% User Flow
    USER((User)) -->|1. Submit Goal| UI
    UI -->|2. POST /strategize| SA
    SA -->|3. Generate Plan| SAG
    SA -->|4. Save Job<br/>status: pending_approval| FS
    FS -->|5. Real-time Listener| UI
    UI -->|6. Display Plan| USER
    USER -->|7. Approve| UI
    UI -->|8. POST /approve<br/>+ ID Token| SA
    SA -->|9. Verify Token| AUTH
    SA -->|10. Transaction Update<br/>status: processing| FS
    SA -->|11. Publish Message| PS

    %% Agent Communication
    PS -->|12. Push Subscription<br/>OIDC Auth| CA
    CA -->|13. Orchestrate| COORD

    %% ADK Orchestration
    COORD -.->|Delegate Caption Task| COPY
    COORD -.->|Delegate Image Task| IMG
    COORD -.->|Delegate Video Task| VID

    COPY -->|Generate Captions| GEM
    IMG -->|Generate Image| IMAGEN
    VID -->|Generate Video| VEO

    GEM -->|Captions JSON| CS
    IMAGEN -->|Image PNG/JPG| CS
    VEO -->|Video MP4| CS

    %% Completion
    CS -->|14. Asset URLs| CA
    CA -->|15. Update Job<br/>status: completed| FS
    FS -->|16. Real-time Update| UI
    UI -->|17. Display Assets| USER

    %% Styling
    classDef cloudRun fill:#4285f4,stroke:#1a73e8,stroke-width:2px,color:#fff
    classDef vertex fill:#ea4335,stroke:#c5221f,stroke-width:2px,color:#fff
    classDef data fill:#34a853,stroke:#188038,stroke-width:2px,color:#fff
    classDef adk fill:#fbbc04,stroke:#f29900,stroke-width:2px,color:#000
    classDef user fill:#9aa0a6,stroke:#5f6368,stroke-width:2px,color:#fff

    class UI,SA,CA cloudRun
    class SAG,GEM,IMAGEN,VEO vertex
    class FS,PS,CS data
    class COORD,COPY,IMG,VID adk
    class USER,AUTH user
```

## Key Components

### Cloud Run Services (3 Independent Services)
1. **Frontend** - Next.js web interface
2. **Strategy Agent** - Marketing plan generation with Gemini
3. **Creative Agent** - Asset generation with ADK multi-agent orchestration

### ADK Multi-Agent System
- **Creative Director**: LlmAgent coordinator orchestrating 3 specialized sub-agents
- **Copy Writer Agent**: Generates social media captions using Gemini
- **Image Creator Agent**: Generates promotional images using Imagen
- **Video Producer Agent**: Generates promotional videos using Veo

### Google Cloud Services
- **Firestore**: Job state management with real-time updates
- **Pub/Sub**: Asynchronous agent-to-agent communication
- **Cloud Storage**: Public asset hosting
- **Vertex AI**: Gemini, Imagen, Veo model access
- **Firebase Auth**: User authentication

## Human-in-the-Loop (HITL) Workflow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Pending   │────▶│   Approval   │────▶│ Processing  │────▶│  Completed   │
│  Approval   │     │   Required   │     │ (Generating)│     │   (Assets)   │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
      │                     │                                         │
      └─────────────────────┴─────────Rejected─────────────────────▶ ❌
```

## Data Flow (Step-by-Step)

1. **User Submission**: User enters marketing goal via Frontend UI
2. **Strategy Generation**: Strategy Agent calls Gemini to generate marketing plan
3. **Pending Approval**: Job saved to Firestore with `status = pending_approval`
4. **Real-time Display**: Frontend displays plan via Firestore listener
5. **Human Approval**: User reviews and approves the plan
6. **Atomic Transaction**: Strategy Agent updates Firestore + publishes to Pub/Sub atomically
7. **Pub/Sub Trigger**: Creative Agent receives message via push subscription (OIDC authenticated)
8. **ADK Orchestration**: Creative Director coordinator delegates tasks to 3 sub-agents in parallel:
   - Copy Writer → Gemini 2.5 Flash → Captions JSON
   - Image Creator → Imagen 4.0 → Image PNG/JPG
   - Video Producer → Veo 3.0 → Video MP4
9. **Asset Upload**: All generated assets uploaded to Cloud Storage with public URLs
10. **Completion**: Creative Agent updates Firestore to `status = completed` with asset URLs
11. **Display Results**: Frontend shows generated assets to user

## Security Features

- **Firebase Authentication**: Anonymous user authentication
- **Firestore Security Rules**: Read-only client access, server-side writes only
- **OIDC Authentication**: Pub/Sub push subscription validates tokens
- **Service Accounts**: Minimal IAM permissions per service
- **ID Token Verification**: Strategy Agent validates Firebase tokens on approval

## Scalability Features

- **Serverless Architecture**: All services auto-scale on Cloud Run
- **Async Processing**: Pub/Sub decouples strategy and creative agents
- **Parallel Execution**: ADK orchestrates 3 agents in parallel for efficiency
- **Timeout Protection**: 120s for Gemini, 90s for Imagen, 120s for Veo
- **Idempotent Design**: Safe duplicate message handling

## Technology Stack

- **Frontend**: Next.js 14, React, TypeScript, Firebase SDK
- **Backend**: FastAPI, Python 3.11+, Google ADK, Pydantic
- **AI Models**: Gemini 2.5 Flash, Imagen 4.0, Veo 3.0
- **Infrastructure**: Cloud Run, Firestore, Pub/Sub, Cloud Storage
- **Orchestration**: Google Agent Development Kit (ADK)
- **Testing**: pytest (83 tests), GitHub Actions CI/CD
