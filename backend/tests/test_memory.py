import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from memory import InMemorySessionStore


class InMemorySessionStoreTests(unittest.TestCase):
    def test_messages_preserve_order_within_one_process(self):
        store = InMemorySessionStore()
        store.get_or_create("test-session")
        store.add_message("test-session", "user", "First question")
        store.add_message("test-session", "assistant", "First answer")

        messages = store.list_messages("test-session")

        self.assertEqual(
            [(message.role, message.content) for message in messages],
            [
                ("user", "First question"),
                ("assistant", "First answer"),
            ],
        )
        self.assertEqual(
            store.get_recent_context("test-session"),
            "USER: First question\nASSISTANT: First answer",
        )

    def test_sessions_are_isolated_and_context_is_bounded(self):
        store = InMemorySessionStore()
        store.get_or_create("first-session")
        store.get_or_create("second-session")
        store.add_message("first-session", "user", "A" * 40)
        store.add_message("second-session", "user", "private second session")

        context = store.get_recent_context(
            "first-session",
            max_message_chars=12,
            max_total_chars=30,
        )

        self.assertIn("[truncated]", context)
        self.assertNotIn("private second session", context)
        self.assertEqual(
            store.get_recent_context("second-session"),
            "USER: private second session",
        )


if __name__ == "__main__":
    unittest.main()
