"""Core URL audit service with concurrency control."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.utils.cache import Cache, create_cache
from app.utils.validator import ValidationError, validate_url


class AuditError(Exception):
    """Raised when audit fails."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class AuditService:
    """Service for auditing URLs with caching and concurrency control."""

    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache or create_cache()
        self.semaphore = asyncio.Semaphore(settings.max_concurrency)

        # Lazily created per event loop to avoid cross-loop reuse issues.
        self.client: Optional[httpx.AsyncClient] = None
        self.client_loop: Optional[asyncio.AbstractEventLoop] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get an HTTP client bound to the current event loop."""
        current_loop = asyncio.get_running_loop()

        if (
            self.client is None
            or self.client.is_closed
            or self.client_loop is not current_loop
        ):
            if self.client is not None and not self.client.is_closed:
                await self.client.aclose()

            limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0, read=settings.audit_timeout_seconds, write=5.0, pool=5.0
                ),
                limits=limits,
                follow_redirects=True,
                headers={"User-Agent": "URL-Audit-Service/1.0"},
            )
            self.client_loop = current_loop

        return self.client

    async def audit(self, raw_url: str, request_id: str) -> Dict[str, Any]:
        """
        Audit a URL and return structured results.

        Args:
            raw_url: The URL to audit
            request_id: Unique request ID for tracing

        Returns:
            Dictionary with audit results

        Raises:
            AuditError: If validation or audit fails
        """
        # Validate URL
        try:
            validated_url = validate_url(raw_url)
        except ValidationError as e:
            raise AuditError(e.code, e.message)

        log = logger.getChild("audit")
        log.info(f"Auditing URL: {validated_url}")

        # Check cache
        cached = self.cache.get(validated_url)
        if cached:
            log.info(f"Cache hit for {validated_url}")
            cached["request_id"] = request_id
            return cached

        # Acquire semaphore for concurrency control
        async with self.semaphore:
            result = await self._perform_audit(validated_url, request_id)

        # Cache the result
        cache_ttl = settings.cache_ttl_seconds
        self.cache.set(validated_url, result, cache_ttl)

        return result

    async def _perform_audit(self, url: str, request_id: str) -> Dict[str, Any]:
        """Perform the actual HTTP audit."""
        start_time = time.time()
        client = await self._get_client()

        try:
            response = await client.get(url)
        except httpx.TimeoutException:
            raise AuditError(
                "TIMEOUT",
                f"Request to {url} timed out after {settings.audit_timeout_seconds}s",
            )
        except httpx.TooManyRedirects:
            raise AuditError(
                "TOO_MANY_REDIRECTS",
                f"Too many redirects (max: {settings.max_redirect_count})",
            )
        except httpx.RequestError as e:
            raise AuditError("REQUEST_FAILED", f"Failed to fetch URL: {str(e)}")

        response_time_ms = int((time.time() - start_time) * 1000)

        # Extract headers
        headers = {k: v for k, v in response.headers.items()}

        result = {
            "url": url,
            "status_code": response.status_code,
            "status": f"{response.status_code} {response.reason_phrase}",
            "response_time_ms": response_time_ms,
            "content_length": len(response.content),
            "content_type": response.headers.get("content-type", ""),
            "headers": headers,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cached": False,
            "request_id": request_id,
        }

        return result

    async def close(self):
        """Close the HTTP client."""
        if self.client is not None and not self.client.is_closed:
            await self.client.aclose()
        self.client = None
        self.client_loop = None


# Global service instance
audit_service = AuditService()
