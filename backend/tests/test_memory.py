import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from memory import RedisSessionStore


class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.lists = {}
        self.expirations = {}

    def hset(self, name, mapping):
        self.hashes.setdefault(name, {}).update(mapping)

    def hgetall(self, name):
        return dict(self.hashes.get(name, {}))

    def rpush(self, name, value):
        self.lists.setdefault(name, []).append(value)

    def ltrim(self, name, start, end):
        values = self.lists.get(name, [])
        if start < 0:
            start = max(0, len(values) + start)
        self.lists[name] = values[start:] if end == -1 else values[start : end + 1]

    def lrange(self, name, start, end):
        values = self.lists.get(name, [])
        return list(values[start:] if end == -1 else values[start : end + 1])

    def expire(self, name, seconds):
        self.expirations[name] = seconds


class RedisSessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.store = RedisSessionStore(
            client=self.redis,
            ttl_seconds=60,
            max_messages=2,
        )

    def test_messages_are_serialized_in_order_and_bounded(self):
        self.store.get_or_create("test-session")
        self.store.add_message("test-session", "user", "Discarded")
        self.store.add_message("test-session", "user", "First question")
        self.store.add_message("test-session", "assistant", "First answer")

        messages = self.store.list_messages("test-session")

        self.assertEqual(
            [(message.role, message.content) for message in messages],
            [("user", "First question"), ("assistant", "First answer")],
        )
        self.assertEqual(
            self.store.get_recent_context("test-session"),
            "USER: First question\nASSISTANT: First answer",
        )
        raw = self.redis.lists["bastion:session:test-session:messages"]
        self.assertEqual(json.loads(raw[0])["content"], "First question")

    def test_sessions_are_isolated_truncated_and_expiring(self):
        self.store.add_message("first-session", "user", "A" * 40)
        self.store.add_message("second-session", "user", "private second session")

        context = self.store.get_recent_context(
            "first-session",
            max_message_chars=12,
            max_total_chars=30,
        )

        self.assertIn("[truncated]", context)
        self.assertNotIn("private second session", context)
        self.assertEqual(
            self.store.get_recent_context("second-session"),
            "USER: private second session",
        )
        self.assertEqual(
            self.redis.expirations["bastion:session:first-session:messages"],
            60,
        )


if __name__ == "__main__":
    unittest.main()
