"""Caching layer with Redis and in-memory fallback."""

import json
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

import redis
from app.core.config import settings
from app.core.logging import logger


class Cache(ABC):
    """Abstract cache interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass

    @abstractmethod
    def health(self) -> bool:
        pass


class RedisCache(Cache):
    """Redis-backed cache implementation."""

    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        # Test connection
        self.client.ping()
        logger.info("Redis cache connected")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            data = self.client.get(_cache_key(key))
            if data:
                result = json.loads(data)
                result["cached"] = True
                return result
            return None
        except redis.RedisError as e:
            logger.warning(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        try:
            self.client.setex(_cache_key(key), ttl, json.dumps(value))
        except redis.RedisError as e:
            logger.warning(f"Redis set error: {e}")

    def delete(self, key: str) -> None:
        try:
            self.client.delete(_cache_key(key))
        except redis.RedisError as e:
            logger.warning(f"Redis delete error: {e}")

    def health(self) -> bool:
        try:
            return self.client.ping()
        except redis.RedisError:
            return False


class InMemoryCache(Cache):
    """In-memory cache fallback for development/testing."""

    def __init__(self):
        self._data: Dict[str, tuple] = {}
        logger.info("In-memory cache initialized")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        cache_key = _cache_key(key)
        if cache_key not in self._data:
            return None
        value, expires_at = self._data[cache_key]
        if time.time() > expires_at:
            del self._data[cache_key]
            return None
        value = dict(value)
        value["cached"] = True
        return value

    def set(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        self._data[_cache_key(key)] = (dict(value), time.time() + ttl)

    def delete(self, key: str) -> None:
        self._data.pop(_cache_key(key), None)

    def health(self) -> bool:
        return True


def _cache_key(url: str) -> str:
    return f"audit:{url}"


def create_cache() -> Cache:
    """Factory to create the best available cache."""
    try:
        return RedisCache()
    except Exception as e:
        logger.warning(f"Redis unavailable, using in-memory cache: {e}")
        return InMemoryCache()
