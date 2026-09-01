from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from typing import Protocol

import configuration  # noqa: F401
from gemini_client import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS


class CacheRedisClient(Protocol):
    def get(self, name: str) -> str | None: ...
    def set(self, name: str, value: str, *, ex: int) -> object: ...
    def delete(self, *names: str) -> object: ...


class RedisQueryEmbeddingCache:
    """Cache query-to-vector conversion only; pgvector retrieval always runs fresh."""

    def __init__(
        self,
        client: CacheRedisClient | None = None,
        *,
        redis_url: str | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        if client is None:
            from redis import Redis

            client = Redis.from_url(
                redis_url or os.getenv("REDIS_URL") or "redis://localhost:6379/0",
                decode_responses=True,
                health_check_interval=30,
            )
        self._client = client
        self._ttl_seconds = ttl_seconds or int(
            os.getenv("QUERY_EMBEDDING_CACHE_TTL_SECONDS", "604800")
        )

    @staticmethod
    def normalize_query(query: str) -> str:
        return " ".join(query.casefold().split())

    @classmethod
    def key_for(
        cls,
        query: str,
        *,
        model: str = DEFAULT_EMBEDDING_MODEL,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> str:
        digest = hashlib.sha256(cls.normalize_query(query).encode("utf-8")).hexdigest()
        return f"bastion:query-embedding:{model}:{dimensions}:{digest}"

    def get(self, query: str) -> list[float] | None:
        key = self.key_for(query)
        payload = self._client.get(key)
        if payload is None:
            return None
        try:
            vector = json.loads(payload)
            if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSIONS:
                raise ValueError("Unexpected embedding dimensions")
            return [float(value) for value in vector]
        except (TypeError, ValueError, json.JSONDecodeError):
            self._client.delete(key)
            return None

    def set(self, query: str, vector: list[float]) -> None:
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Expected {EMBEDDING_DIMENSIONS} embedding dimensions, got {len(vector)}."
            )
        self._client.set(
            self.key_for(query),
            json.dumps(vector, separators=(",", ":")),
            ex=self._ttl_seconds,
        )


@lru_cache(maxsize=1)
def get_query_embedding_cache() -> RedisQueryEmbeddingCache:
    return RedisQueryEmbeddingCache()
