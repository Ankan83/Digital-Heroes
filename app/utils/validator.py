"""URL validation with SSRF protection."""

import socket
from urllib.parse import urlparse


BLOCKED_HOSTS = [
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
    "172.30.", "172.31.", "192.168.", "169.254.",
]


class ValidationError(Exception):
    """Raised when URL validation fails."""
    def __init__(self, message: str, code: str = "INVALID_URL"):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_url(raw_url: str) -> str:
    """
    Validate and normalize a URL.

    Args:
        raw_url: The URL string to validate

    Returns:
        Normalized URL string

    Raises:
        ValidationError: If URL is invalid or points to internal address
    """
    if not raw_url or not raw_url.strip():
        raise ValidationError("URL is required", code="INVALID_URL")

    raw_url = raw_url.strip()

    # Check if a scheme is already present (any scheme)
    has_scheme = "://" in raw_url

    if has_scheme:
        # Validate the scheme is http or https
        scheme = raw_url.split("://", 1)[0].lower()
        if scheme not in ("http", "https"):
            raise ValidationError("Only HTTP and HTTPS URLs are supported", code="INVALID_URL")
    else:
        # Add https:// if no scheme
        raw_url = "https://" + raw_url

    try:
        parsed = urlparse(raw_url)
    except Exception:
        raise ValidationError("Invalid URL format", code="INVALID_URL")

    if parsed.scheme not in ("http", "https"):
        raise ValidationError("Only HTTP and HTTPS URLs are supported", code="INVALID_URL")

    host = parsed.hostname
    if not host:
        raise ValidationError("URL must have a host", code="INVALID_URL")

    # Check for blocked hosts (SSRF protection)
    if _is_blocked_host(host):
        raise ValidationError(
            "Access to internal or reserved addresses is not allowed",
            code="FORBIDDEN_URL"
        )

    # DNS resolution check to prevent DNS rebinding
    try:
        resolved = socket.getaddrinfo(host, None)
        for _, _, _, _, sockaddr in resolved:
            ip = sockaddr[0]
            if _is_blocked_host(ip):
                raise ValidationError(
                    "Access to internal or reserved addresses is not allowed",
                    code="FORBIDDEN_URL"
                )
    except socket.gaierror:
        # If DNS fails, we allow it (the audit will catch the actual failure)
        pass

    # Reconstruct normalized URL
    normalized = f"{parsed.scheme}://{host}"
    if parsed.port and not ((parsed.scheme == "http" and parsed.port == 80) or 
                            (parsed.scheme == "https" and parsed.port == 443)):
        normalized += f":{parsed.port}"
    if parsed.path:
        normalized += parsed.path
    if parsed.query:
        normalized += f"?{parsed.query}"

    return normalized


def _is_blocked_host(host: str) -> bool:
    """Check if host is in the blocked list."""
    host_lower = host.lower()
    for blocked in BLOCKED_HOSTS:
        if host_lower == blocked or host_lower.startswith(blocked):
            return True
    return False
