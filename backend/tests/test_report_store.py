import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from report_store import PostgresReportStore


class ConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_args):
        return False


class PostgresReportStoreTests(unittest.TestCase):
    def test_save_writes_request_memo_and_report_payloads(self):
        connection = Mock()
        pool = Mock()
        pool.connection.return_value = ConnectionContext(connection)
        request = Mock()
        request.model_dump.return_value = {"buyer_context": "Buyer"}
        memo = Mock()
        memo.recommendation = "proceed"
        memo.model_dump.return_value = {"recommendation": "proceed"}
        report = Mock()
        report.title = "Investment report"
        report.model_dump.return_value = {"title": "Investment report"}

        PostgresReportStore(pool=pool).save(
            workflow_run_id="00000000-0000-0000-0000-000000000001",
            session_id="session-1",
            request=request,
            investment_memo=memo,
            report=report,
        )

        parameters = connection.execute.call_args.args[1]
        self.assertEqual(parameters[0], "00000000-0000-0000-0000-000000000001")
        self.assertEqual(parameters[1:4], ("session-1", "Investment report", "proceed"))
        self.assertEqual(parameters[4].obj, {"buyer_context": "Buyer"})
        self.assertEqual(parameters[5].obj, {"recommendation": "proceed"})
        self.assertEqual(parameters[6].obj, {"title": "Investment report"})

    def test_get_reads_report_by_workflow_id(self):
        cursor = Mock()
        cursor.fetchone.return_value = {"workflow_run_id": "run-1"}
        connection = Mock()
        connection.execute.return_value = cursor
        pool = Mock()
        pool.connection.return_value = ConnectionContext(connection)

        result = PostgresReportStore(pool=pool).get("run-1")

        self.assertEqual(result["workflow_run_id"], "run-1")
        self.assertEqual(connection.execute.call_args.args[1], ("run-1",))


if __name__ == "__main__":
    unittest.main()
