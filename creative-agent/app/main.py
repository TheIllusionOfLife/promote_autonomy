"""Creative Agent FastAPI application."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.routers import consume

settings = get_settings()

app = FastAPI(
    title="Creative Agent",
    description="Generates marketing assets from task lists",
    version="0.1.0",
)

# No CORS middleware needed - Creative Agent only accepts Pub/Sub push requests
# It is not accessed by browsers, so CORS is unnecessary

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
