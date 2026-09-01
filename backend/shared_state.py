from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Protocol
from uuid import uuid4

import configuration  # noqa: F401


_RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""

_RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


class SharedRedisClient(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...
    def set(self, name: str, value: str, *, nx: bool, ex: int) -> object: ...


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    count: int
    limit: int
    retry_after_seconds: int


class DistributedLockUnavailable(RuntimeError):
    pass


class RedisSharedState:
    """Cross-worker counters and locks; conversation messages live in memory.py."""

    def __init__(
        self,
        client: SharedRedisClient | None = None,
        *,
        redis_url: str | None = None,
        key_prefix: str = "bastion",
    ) -> None:
        if client is None:
            from redis import Redis

            client = Redis.from_url(
                redis_url or os.getenv("REDIS_URL") or "redis://localhost:6379/0",
                decode_responses=True,
                health_check_interval=30,
            )
        self._client = client
        self._key_prefix = key_prefix

    def check_rate_limit(
        self,
        scope: str,
        identity: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        key = f"{self._key_prefix}:ratelimit:{scope}:{identity}"
        raw = self._client.eval(
            _RATE_LIMIT_SCRIPT,
            1,
            key,
            window_seconds,
        )
        count, ttl = (int(value) for value in raw)  # type: ignore[arg-type]
        return RateLimitResult(
            allowed=count <= limit,
            count=count,
            limit=limit,
            retry_after_seconds=max(ttl, 1),
        )

    @contextmanager
    def lock(
        self,
        scope: str,
        resource_id: str,
        *,
        ttl_seconds: int,
    ) -> Iterator[None]:
        key = f"{self._key_prefix}:lock:{scope}:{resource_id}"
        token = str(uuid4())
        acquired = self._client.set(key, token, nx=True, ex=ttl_seconds)
        if not acquired:
            raise DistributedLockUnavailable(
                f"Another worker is already processing {scope} '{resource_id}'."
            )
        try:
            yield
        finally:
            self._client.eval(_RELEASE_LOCK_SCRIPT, 1, key, token)


class LazyRedisSharedState:
    def __init__(self) -> None:
        self._state: RedisSharedState | None = None

    def _get_state(self) -> RedisSharedState:
        if self._state is None:
            self._state = RedisSharedState()
        return self._state

    def check_rate_limit(self, *args, **kwargs) -> RateLimitResult:
        return self._get_state().check_rate_limit(*args, **kwargs)

    def lock(self, *args, **kwargs):
        return self._get_state().lock(*args, **kwargs)


shared_state = LazyRedisSharedState()
