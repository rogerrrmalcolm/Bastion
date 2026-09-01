import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from shared_state import DistributedLockUnavailable, RedisSharedState


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def set(self, name, value, *, nx, ex):
        if nx and name in self.values:
            return None
        self.values[name] = value
        self.expirations[name] = ex
        return True

    def eval(self, script, numkeys, *keys_and_args):
        key = keys_and_args[0]
        if "INCR" in script:
            window = int(keys_and_args[1])
            count = int(self.values.get(key, 0)) + 1
            self.values[key] = count
            self.expirations.setdefault(key, window)
            return [count, self.expirations[key]]

        token = keys_and_args[1]
        if self.values.get(key) == token:
            del self.values[key]
            return 1
        return 0


class RedisSharedStateTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.state = RedisSharedState(client=self.redis)

    def test_rate_limit_counter_is_shared_by_scope_and_identity(self):
        first = self.state.check_rate_limit(
            "analyze", "client-a", limit=2, window_seconds=60
        )
        second = self.state.check_rate_limit(
            "analyze", "client-a", limit=2, window_seconds=60
        )
        rejected = self.state.check_rate_limit(
            "analyze", "client-a", limit=2, window_seconds=60
        )
        separate = self.state.check_rate_limit(
            "chat", "client-a", limit=2, window_seconds=60
        )

        self.assertTrue(first.allowed)
        self.assertEqual(second.count, 2)
        self.assertFalse(rejected.allowed)
        self.assertEqual(rejected.retry_after_seconds, 60)
        self.assertEqual(separate.count, 1)

    def test_distributed_lock_rejects_second_owner_and_releases_safely(self):
        with self.state.lock("session-analysis", "session-1", ttl_seconds=30):
            with self.assertRaises(DistributedLockUnavailable):
                with self.state.lock(
                    "session-analysis", "session-1", ttl_seconds=30
                ):
                    pass

        with self.state.lock("session-analysis", "session-1", ttl_seconds=30):
            pass


if __name__ == "__main__":
    unittest.main()
