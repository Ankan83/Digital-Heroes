"""Custom middleware for request ID, logging, rate limiting, and timeouts."""

import time
import traceback
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import set_request_id, get_request_id, logger
from app.utils.rate_limiter import rate_limiter


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with structured fields."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = get_request_id()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"{request.method} {request.url.path} | "
            f"status={response.status_code} | "
            f"duration={duration_ms:.2f}ms | "
            f"client={request.client.host if request.client else 'unknown'}"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit requests per client IP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)

        if not rate_limiter.is_allowed(client_ip):
            request_id = get_request_id()
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded. Please slow down.",
                        "request_id": request_id
                    }
                },
                headers={"Retry-After": "60"}
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP considering proxies."""
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()

        xri = request.headers.get("X-Real-Ip")
        if xri:
            return xri

        return request.client.host if request.client else "unknown"


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Add request timeout."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception:
            request_id = get_request_id()
            logger.error(f"Request timeout or error: {traceback.format_exc()}")
            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "REQUEST_TIMEOUT",
                        "message": "Request timed out",
                        "request_id": request_id
                    }
                }
            )


class CORSMiddleware(BaseHTTPMiddleware):
    """Add CORS headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Request-ID"
        response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Cache"
        return response
