# Promote Autonomy Frontend

Next.js application providing the Human-in-the-Loop (HITL) approval interface for marketing automation.

## Features

- **Anonymous Authentication**: Users can access the app without creating accounts
- **Real-time Job Updates**: Firestore listeners update UI automatically
- **Strategy Generation**: Call Strategy Agent to generate marketing plans
- **Approval Workflow**: Review and approve AI-generated strategies
- **Asset Display**: View generated captions, images, and videos

## Getting Started

### Installation

```bash
npm install
```

### Configuration

Copy `.env.local.example` to `.env.local` and fill in your Firebase credentials:

```bash
cp .env.local.example .env.local
```

Required environment variables:
- `NEXT_PUBLIC_FIREBASE_*`: Firebase project configuration
- `NEXT_PUBLIC_STRATEGY_AGENT_URL`: Strategy Agent API URL (default: http://localhost:8000)

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

## Architecture

### Client-Side Firebase

The frontend uses Firebase client SDK for:
- **Authentication**: Anonymous sign-in for quick access
- **Firestore**: Real-time job status updates (read-only)

### API Integration

All write operations go through the Strategy Agent:
- `POST /api/strategize`: Generate marketing strategy
- `POST /api/approve`: Approve strategy and trigger asset generation

### State Flow

```
User Input → Strategy Agent → Firestore (pending_approval)
                                   ↓
User Approval → Strategy Agent → Pub/Sub → Creative Agent
                                   ↓
                           Firestore (processing → completed)
                                   ↓
                           Frontend updates via listener
```

## Security

- **Firestore Security Rules**: Users can only read their own jobs
- **API Authentication**: `/approve` endpoint verifies Firebase ID tokens
- **No Direct Writes**: Frontend never writes to Firestore directly

## Deployment

### Vercel (Recommended)

```bash
vercel
```

### Cloud Run

```bash
gcloud run deploy frontend \
  --source=. \
  --region=asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars="NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project,..."
```

## License

MIT
