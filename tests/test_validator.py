"""Tests for URL validator."""

import pytest

from app.utils.validator import ValidationError, validate_url


class TestValidateURL:
    """Test cases for URL validation."""

    def test_valid_https_url(self):
        result = validate_url("https://example.com")
        assert result == "https://example.com"

    def test_valid_http_url(self):
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_missing_scheme(self):
        result = validate_url("example.com")
        assert result == "https://example.com"

    def test_with_path(self):
        result = validate_url("https://example.com/path")
        assert result == "https://example.com/path"

    def test_with_query(self):
        result = validate_url("https://example.com?foo=bar")
        assert result == "https://example.com?foo=bar"

    def test_empty_url(self):
        with pytest.raises(ValidationError, match="URL is required"):
            validate_url("")

    def test_whitespace_url(self):
        with pytest.raises(ValidationError, match="URL is required"):
            validate_url("   ")

    def test_localhost_blocked(self):
        with pytest.raises(ValidationError, match="internal or reserved"):
            validate_url("http://localhost:8080")

    def test_127_blocked(self):
        with pytest.raises(ValidationError, match="internal or reserved"):
            validate_url("http://127.0.0.1")

    def test_private_ip_blocked(self):
        with pytest.raises(ValidationError, match="internal or reserved"):
            validate_url("http://192.168.1.1")

    def test_10x_blocked(self):
        with pytest.raises(ValidationError, match="internal or reserved"):
            validate_url("http://10.0.0.1")

    def test_ftp_scheme_rejected(self):
        with pytest.raises(ValidationError, match="Only HTTP and HTTPS"):
            validate_url("ftp://example.com")

    def test_just_path_rejected(self):
        with pytest.raises(ValidationError):
            validate_url("/path/to/something")
