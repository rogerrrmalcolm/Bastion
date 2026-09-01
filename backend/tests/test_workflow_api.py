import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from main import app
import main


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

    def test_final_report_endpoint_reads_postgres_store(self):
        workflow_run_id = "00000000-0000-0000-0000-000000000001"
        store = Mock()
        store.get.return_value = {
            "workflow_run_id": workflow_run_id,
            "title": "Stored report",
        }

        with patch.object(main, "get_report_store", return_value=store):
            response = TestClient(app).get(f"/reports/{workflow_run_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Stored report")
        store.get.assert_called_once_with(workflow_run_id)

    def test_missing_final_report_returns_404(self):
        workflow_run_id = "00000000-0000-0000-0000-000000000002"
        store = Mock()
        store.get.return_value = None

        with patch.object(main, "get_report_store", return_value=store):
            response = TestClient(app).get(f"/reports/{workflow_run_id}")

        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
