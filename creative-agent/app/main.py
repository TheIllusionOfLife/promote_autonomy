"""Creative Agent FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import consume

settings = get_settings()

app = FastAPI(
    title="Creative Agent",
    description="Generates marketing assets from task lists",
    version="0.1.0",
)

# CORS middleware
# Use FRONTEND_URL from environment for production security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(consume.router, prefix="/api", tags=["consume"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "creative-agent",
        "mock_mode": {
            "imagen": settings.USE_MOCK_IMAGEN,
            "veo": settings.USE_MOCK_VEO,
            "firestore": settings.USE_MOCK_FIRESTORE,
            "storage": settings.USE_MOCK_STORAGE,
        },
    }
