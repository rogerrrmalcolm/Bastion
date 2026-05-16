from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
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


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionMemory] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: str | None = None) -> SessionMemory:
        with self._lock:
            resolved_session_id = session_id or str(uuid4())
            session = self._sessions.get(resolved_session_id)

            if session is None:
                session = SessionMemory(session_id=resolved_session_id)
                self._sessions[resolved_session_id] = session

            return session

    def add_message(self, session_id: str, role: Role, content: str) -> MemoryMessage:
        with self._lock:
            session = self._sessions[session_id]
            message = MemoryMessage(role=role, content=content)
            session.messages.append(message)
            session.updated_at = datetime.now(timezone.utc)
            return message

    def get_recent_context(
        self,
        session_id: str,
        limit: int = 6,
        max_message_chars: int = 1200,
        max_total_chars: int = 6000,
    ) -> str:
        with self._lock:
            session = self._sessions[session_id]
            messages = session.messages[-limit:]

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
        with self._lock:
            session = self._sessions[session_id]
            return list(session.messages)


memory_store = InMemorySessionStore()
