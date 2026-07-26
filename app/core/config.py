"""Application configuration loaded from environment variables."""

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with sensible defaults."""

    port: int = Field(default=8080, env="PORT")
    host: str = Field(default="0.0.0.0", env="HOST")

    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")

    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")

    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")

    audit_timeout_seconds: float = Field(default=10.0, env="AUDIT_TIMEOUT_SECONDS")
    max_redirect_count: int = Field(default=10, env="MAX_REDIRECT_COUNT")
    max_concurrency: int = Field(default=100, env="MAX_CONCURRENCY")

    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="development", env="ENVIRONMENT")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
