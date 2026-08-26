from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import uuid4

Role = Literal["user", "assistant", "system"]


@dataclass
class MemoryMessage:
    role: Role
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionMemory:
    session_id: str
    messages: list[MemoryMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RedisClient(Protocol):
    def hset(self, name: str, mapping: dict[str, str]) -> object: ...
    def hgetall(self, name: str) -> dict[str, str]: ...
    def rpush(self, name: str, value: str) -> object: ...
    def ltrim(self, name: str, start: int, end: int) -> object: ...
    def lrange(self, name: str, start: int, end: int) -> list[str]: ...
    def expire(self, name: str, seconds: int) -> object: ...


class RedisSessionStore:
    """Bounded, expiring conversation memory shared across API replicas."""

    def __init__(
        self,
        client: RedisClient | None = None,
        *,
        redis_url: str | None = None,
        ttl_seconds: int | None = None,
        max_messages: int | None = None,
    ) -> None:
        if client is None:
            from redis import Redis

            resolved_url = (
                redis_url
                or os.getenv("REDIS_URL")
                or "redis://localhost:6379/0"
            )
            client = Redis.from_url(
                resolved_url,
                decode_responses=True,
                health_check_interval=30,
            )
        self._client = client
        self._ttl_seconds = ttl_seconds or int(
            os.getenv("SESSION_TTL_SECONDS", "86400")
        )
        self._max_messages = max_messages or int(
            os.getenv("SESSION_MAX_MESSAGES", "50")
        )

    @staticmethod
    def _metadata_key(session_id: str) -> str:
        return f"bastion:session:{session_id}:metadata"

    @staticmethod
    def _messages_key(session_id: str) -> str:
        return f"bastion:session:{session_id}:messages"

    def _refresh_ttl(self, session_id: str) -> None:
        self._client.expire(self._metadata_key(session_id), self._ttl_seconds)
        self._client.expire(self._messages_key(session_id), self._ttl_seconds)

    def get_or_create(self, session_id: str | None = None) -> SessionMemory:
        resolved_session_id = session_id or str(uuid4())
        metadata_key = self._metadata_key(resolved_session_id)
        metadata = self._client.hgetall(metadata_key)
        now = datetime.now(timezone.utc)

        if not metadata:
            timestamp = now.isoformat()
            metadata = {"created_at": timestamp, "updated_at": timestamp}
            self._client.hset(metadata_key, mapping=metadata)

        self._refresh_ttl(resolved_session_id)
        return SessionMemory(
            session_id=resolved_session_id,
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
        )

    def add_message(self, session_id: str, role: Role, content: str) -> MemoryMessage:
        self.get_or_create(session_id)
        message = MemoryMessage(role=role, content=content)
        payload = asdict(message)
        payload["created_at"] = message.created_at.isoformat()
        messages_key = self._messages_key(session_id)
        self._client.rpush(messages_key, json.dumps(payload))
        self._client.ltrim(messages_key, -self._max_messages, -1)
        self._client.hset(
            self._metadata_key(session_id),
            mapping={"updated_at": message.created_at.isoformat()},
        )
        self._refresh_ttl(session_id)
        return message

    def get_recent_context(
        self,
        session_id: str,
        limit: int = 6,
        max_message_chars: int = 1200,
        max_total_chars: int = 6000,
    ) -> str:
        messages = self.list_messages(session_id)[-limit:]
        if not messages:
            return "No previous conversation in this session."

        entries: list[str] = []
        total_chars = 0
        for message in reversed(messages):
            content = " ".join(message.content.split())
            if len(content) > max_message_chars:
                content = f"{content[:max_message_chars].rstrip()}... [truncated]"
            entry = f"{message.role.upper()}: {content}"
            if entries and total_chars + len(entry) > max_total_chars:
                break
            entries.append(entry)
            total_chars += len(entry)

        return "\n".join(reversed(entries))

    def list_messages(self, session_id: str) -> list[MemoryMessage]:
        self.get_or_create(session_id)
        payloads = self._client.lrange(self._messages_key(session_id), 0, -1)
        messages = []
        for payload in payloads:
            value = json.loads(payload)
            messages.append(
                MemoryMessage(
                    role=value["role"],
                    content=value["content"],
                    created_at=datetime.fromisoformat(value["created_at"]),
                )
            )
        self._refresh_ttl(session_id)
        return messages


class LazyRedisSessionStore:
    """Delay Redis client creation until a request actually uses session memory."""

    def __init__(self) -> None:
        self._store: RedisSessionStore | None = None

    def _get_store(self) -> RedisSessionStore:
        if self._store is None:
            self._store = RedisSessionStore()
        return self._store

    def get_or_create(self, session_id: str | None = None) -> SessionMemory:
        return self._get_store().get_or_create(session_id)

    def add_message(self, session_id: str, role: Role, content: str) -> MemoryMessage:
        return self._get_store().add_message(session_id, role, content)

    def get_recent_context(
        self,
        session_id: str,
        limit: int = 6,
        max_message_chars: int = 1200,
        max_total_chars: int = 6000,
    ) -> str:
        return self._get_store().get_recent_context(
            session_id,
            limit,
            max_message_chars,
            max_total_chars,
        )

    def list_messages(self, session_id: str) -> list[MemoryMessage]:
        return self._get_store().list_messages(session_id)


memory_store = LazyRedisSessionStore()
