import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from embedding_cache import RedisQueryEmbeddingCache
from gemini_client import EMBEDDING_DIMENSIONS


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def get(self, name):
        return self.values.get(name)

    def set(self, name, value, *, ex):
        self.values[name] = value
        self.expirations[name] = ex

    def delete(self, *names):
        for name in names:
            self.values.pop(name, None)


class RedisQueryEmbeddingCacheTests(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.cache = RedisQueryEmbeddingCache(client=self.redis, ttl_seconds=90)

    def test_normalized_queries_share_a_model_versioned_key(self):
        first = self.cache.key_for(" Revenue   Growth ")
        second = self.cache.key_for("revenue growth")

        self.assertEqual(first, second)
        self.assertIn("gemini-embedding-001", first)
        self.assertIn(f":{EMBEDDING_DIMENSIONS}:", first)

    def test_vector_round_trip_uses_ttl(self):
        vector = [0.0] * EMBEDDING_DIMENSIONS
        self.cache.set("revenue growth", vector)

        self.assertEqual(self.cache.get("Revenue Growth"), vector)
        key = self.cache.key_for("revenue growth")
        self.assertEqual(self.redis.expirations[key], 90)

    def test_invalid_cached_vector_is_evicted(self):
        key = self.cache.key_for("risk")
        self.redis.values[key] = json.dumps([1.0])

        self.assertIsNone(self.cache.get("risk"))
        self.assertNotIn(key, self.redis.values)


if __name__ == "__main__":
    unittest.main()
