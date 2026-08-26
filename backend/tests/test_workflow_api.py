import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from main import app


class WorkflowApiTests(unittest.TestCase):
    def test_graph_manifest_endpoint_describes_runtime_topology(self):
        response = TestClient(app).get("/workflow/graph")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state_model"], "BastionGraphState")
        self.assertEqual(payload["state_scope"], "single_run")
        self.assertTrue(payload["checkpointing_enabled"])
        self.assertEqual(payload["checkpoint_backend"], "postgresql")
        self.assertEqual(
            payload["conversation_memory_backend"],
            "redis",
        )
        self.assertIn(
            {
                "name": "market_agent",
                "kind": "agent",
                "description": (
                    "Writes the market analysis into shared graph state."
                ),
            },
            payload["nodes"],
        )
        self.assertTrue(
            any(
                edge["source"] == "market_research"
                and edge["target"] == "market_research"
                and edge["condition"]
                for edge in payload["edges"]
            )
        )

if __name__ == "__main__":
    unittest.main()
