"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import logger
from app.api.routes import router
from app.api.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    TimeoutMiddleware,
    CORSMiddleware as CustomCORSMiddleware,
)
from app.services.audit_service import audit_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info("Starting URL Audit Service v1.0.0")
    yield
    logger.info("Shutting down URL Audit Service")
    await audit_service.close()


app = FastAPI(
    title="URL Audit Service",
    description="Production-grade URL auditing with caching, rate limiting, and security",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount static files (CSS, JS)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Add middleware (order matters - first added = outermost)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CustomCORSMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TimeoutMiddleware)

# Include routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
