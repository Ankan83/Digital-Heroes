"""API route definitions."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, validator
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import get_request_id, logger
from app.services.audit_service import audit_service, AuditError


router = APIRouter()

# Path to static files
STATIC_DIR = Path(__file__).parent.parent.parent / "static"


class AuditRequest(BaseModel):
    """Request model for URL audit."""
    url: str

    @validator("url")
    def url_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        return v.strip()


@router.post("/api/v1/audit")
async def audit_url(request: Request, audit_req: AuditRequest):
    """
    Audit a URL and return HTTP metadata.

    - **url**: The URL to audit (required)

    Returns structured audit results with response time, headers, and SSL info.
    """
    request_id = get_request_id()

    try:
        result = await audit_service.audit(audit_req.url, request_id)
    except AuditError as e:
        status_map = {
            "INVALID_URL": 400,
            "FORBIDDEN_URL": 403,
            "TIMEOUT": 504,
            "TOO_MANY_REDIRECTS": 400,
            "REQUEST_FAILED": 502,
        }
        status_code = status_map.get(e.code, 400)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "request_id": request_id
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during audit: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id
                }
            }
        )

    # Set cache header
    headers = {"X-Cache": "HIT" if result.get("cached") else "MISS"}
    return JSONResponse(content=result, headers=headers)


@router.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    checks = {"api": "healthy"}
    status = "healthy"

    try:
        cache_healthy = audit_service.cache.health()
        checks["cache"] = "healthy" if cache_healthy else "unhealthy"
        if not cache_healthy:
            status = "degraded"
    except Exception as e:
        checks["cache"] = f"unhealthy: {str(e)}"
        status = "degraded"

    return {
        "status": status,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }


@router.get("/", response_class=HTMLResponse)
async def index():
    """Serve the interactive HTML UI from static files."""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>URL Audit Service</h1><p>Static files not found.</p>")
