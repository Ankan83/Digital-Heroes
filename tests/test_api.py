"""Tests for API endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service

client = TestClient(app)


class TestHealthEndpoint:
    """Test cases for health check."""

    def test_health_returns_200(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "checks" in data

    def test_health_has_request_id(self):
        response = client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 36


class TestAuditEndpoint:
    """Test cases for audit endpoint."""

    def test_audit_valid_url(self):
        response = client.post("/api/v1/audit", json={"url": "https://httpbin.org/get"})
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "status_code" in data
        assert "response_time_ms" in data
        assert data["cached"] is False
        assert "request_id" in data

    def test_audit_missing_url(self):
        # Pydantic v1 returns 422 for validation errors
        response = client.post("/api/v1/audit", json={"url": ""})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # FastAPI validation error format

    def test_audit_blocked_url(self):
        response = client.post("/api/v1/audit", json={"url": "http://localhost:8080"})
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "FORBIDDEN_URL"

    def test_audit_invalid_method(self):
        response = client.get("/api/v1/audit")
        assert response.status_code == 405

    def test_audit_caching(self):
        # Clear cache first to ensure clean state
        audit_service.cache.delete("https://httpbin.org/get")

        # First request
        response1 = client.post("/api/v1/audit", json={"url": "https://httpbin.org/get"})
        assert response1.status_code == 200
        assert response1.headers["X-Cache"] == "MISS"

        # Second request should be cached
        response2 = client.post("/api/v1/audit", json={"url": "https://httpbin.org/get"})
        assert response2.status_code == 200
        assert response2.headers["X-Cache"] == "HIT"

    def test_custom_request_id(self):
        custom_id = "my-custom-id-123"
        response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id


class TestIndexEndpoint:
    """Test cases for index page."""

    def test_index_returns_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "URL Audit Service" in response.text

    def test_index_has_footer_credit(self):
        response = client.get("/")
        assert "Built for" in response.text
        assert "digitalheroesco.com" in response.text
