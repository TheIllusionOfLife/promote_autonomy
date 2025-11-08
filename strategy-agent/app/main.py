"""FastAPI application entry point for Strategy Agent."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import approve, strategize

settings = get_settings()

app = FastAPI(
    title="Promote Autonomy - Strategy Agent",
    description="AI strategy generation with Human-in-the-Loop approval",
    version="0.1.0",
)

# CORS middleware for frontend communication
# Use FRONTEND_URL from environment for production security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(strategize.router, prefix="/api", tags=["strategy"])
app.include_router(approve.router, prefix="/api", tags=["approval"])


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "strategy-agent",
        "mock_mode": {
            "gemini": settings.USE_MOCK_GEMINI,
            "firestore": settings.USE_MOCK_FIRESTORE,
            "pubsub": settings.USE_MOCK_PUBSUB,
        },
    }


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Promote Autonomy - Strategy Agent",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "strategize": "/api/strategize",
            "approve": "/api/approve",
            "docs": "/docs",
        },
    }
