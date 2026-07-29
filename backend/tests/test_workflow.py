import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agents import workflow


class FakeResearchContext:
    def __init__(
        self,
        label: str,
        *,
        succeeded: bool = True,
        errors: list[str] | None = None,
    ) -> None:
        self.label = label
        self.retrieval_succeeded = succeeded
        self.retrieval_errors = errors or []

    def to_prompt_json(self) -> str:
        return json.dumps(
            {
                "label": self.label,
                "retrieval_succeeded": self.retrieval_succeeded,
                "retrieval_errors": self.retrieval_errors,
            }
        )


class DiligenceGraphTests(unittest.TestCase):
    def _initial_state(
        self,
        *,
        max_retrieval_attempts: int = 3,
    ) -> workflow.BastionGraphState:
        return {
            "session_id": "test-session",
            "company_text": "Synthetic buyer and target context for graph testing.",
            "research_contexts": {},
            "retrieval_attempts": {},
            "retrieval_statuses": {},
            "retrieval_errors": {},
            "max_retrieval_attempts": max_retrieval_attempts,
            "execution_trace": [],
            "workflow_warnings": [],
        }

    def _invoke_with_fakes(
        self,
        research_builders,
        specialist_runners,
        memo_runner,
        report_builder,
        state,
        orchestrator_runner=None,
    ):
        orchestrator_runner = orchestrator_runner or (
            lambda _: workflow.DEFAULT_PLAN
        )
        graph = workflow.build_diligence_graph()
        with (
            patch.object(
                workflow,
                "run_orchestrator_agent",
                side_effect=orchestrator_runner,
            ),
            patch.dict(
                workflow.RESEARCH_BUILDERS,
                research_builders,
                clear=True,
            ),
            patch.dict(
                workflow.SPECIALIST_RUNNERS,
                specialist_runners,
                clear=True,
            ),
            patch.dict(
                workflow.SYNTHESIS_RUNNERS,
                {"memo_agent": memo_runner},
                clear=True,
            ),
            patch.object(
                workflow,
                "build_report_package",
                side_effect=report_builder,
            ),
        ):
            return graph.invoke(
                state,
                config={"recursion_limit": workflow.GRAPH_RECURSION_LIMIT},
            )

    def test_agents_run_in_order_with_shared_upstream_state(self):
        events: list[str] = []
        received_contexts: dict[str, str] = {}

        def orchestrator(_):
            events.append("orchestrator_agent")
            return workflow.DEFAULT_PLAN

        def research_builder(agent_name):
            def build(_):
                events.append(f"{agent_name}_research")
                return FakeResearchContext(f"{agent_name}-packet")

            return build

        def specialist(agent_name, output):
            def run(context, research_context):
                events.append(agent_name)
                received_contexts[agent_name] = context
                self.assertIn(f"{agent_name}-packet", research_context)
                return output

            return run

        def memo_runner(**kwargs):
            events.append("memo_agent")
            self.assertEqual(kwargs["market_analysis"], "market-output")
            self.assertEqual(kwargs["financial_analysis"], "financial-output")
            self.assertEqual(kwargs["risk_analysis"], "risk-output")
            return "memo-output"

        def report_builder(*args):
            events.append("build_report")
            self.assertEqual(args[1:5], (
                "market-output",
                "financial-output",
                "risk-output",
                "memo-output",
            ))
            return "report-output"

        result = self._invoke_with_fakes(
            research_builders={
                agent_name: research_builder(agent_name)
                for agent_name in workflow.SPECIALIST_OUTPUT_KEYS
            },
            specialist_runners={
                "market_agent": specialist("market_agent", "market-output"),
                "financial_agent": specialist(
                    "financial_agent",
                    "financial-output",
                ),
                "risk_agent": specialist("risk_agent", "risk-output"),
            },
            memo_runner=memo_runner,
            report_builder=report_builder,
            state=self._initial_state(),
            orchestrator_runner=orchestrator,
        )

        self.assertEqual(
            events,
            [
                "orchestrator_agent",
                "market_agent_research",
                "market_agent",
                "financial_agent_research",
                "financial_agent",
                "risk_agent_research",
                "risk_agent",
                "memo_agent",
                "build_report",
            ],
        )
        self.assertIn(
            "market_agent output:\nmarket-output",
            received_contexts["financial_agent"],
        )
        self.assertIn(
            "financial_agent output:\nfinancial-output",
            received_contexts["risk_agent"],
        )
        self.assertEqual(
            result["execution_trace"],
            [
                "orchestrator_agent",
                "market_research:1",
                "market_agent",
                "financial_research:1",
                "financial_agent",
                "risk_research:1",
                "risk_agent",
                "memo_agent",
                "build_report",
            ],
        )

    def test_failed_research_cycles_before_specialist_runs(self):
        market_attempts = 0
        events: list[str] = []

        def market_research(_):
            nonlocal market_attempts
            market_attempts += 1
            events.append(f"market_research:{market_attempts}")
            if market_attempts == 1:
                return FakeResearchContext(
                    "market-failed",
                    succeeded=False,
                    errors=["temporary provider failure"],
                )
            return FakeResearchContext("market-recovered")

        def successful_research(label):
            return lambda _: FakeResearchContext(label)

        def specialist(label):
            def run(_, __):
                events.append(label)
                return f"{label}-output"

            return run

        result = self._invoke_with_fakes(
            research_builders={
                "market_agent": market_research,
                "financial_agent": successful_research("financial"),
                "risk_agent": successful_research("risk"),
            },
            specialist_runners={
                agent_name: specialist(agent_name)
                for agent_name in workflow.SPECIALIST_OUTPUT_KEYS
            },
            memo_runner=lambda **_: "memo-output",
            report_builder=lambda *_: "report-output",
            state=self._initial_state(),
        )

        self.assertEqual(market_attempts, 2)
        self.assertEqual(
            events[:3],
            ["market_research:1", "market_research:2", "market_agent"],
        )
        self.assertEqual(result["retrieval_attempts"]["market_agent"], 2)
        self.assertEqual(
            result["retrieval_statuses"]["market_agent"],
            "succeeded",
        )
        self.assertNotIn("market_agent", result["retrieval_errors"])

    def test_exhausted_research_stops_retrying_and_preserves_limitation(self):
        market_attempts = 0
        received_market_packet = ""

        def failed_market_research(_):
            nonlocal market_attempts
            market_attempts += 1
            return FakeResearchContext(
                "market-failed",
                succeeded=False,
                errors=["provider unavailable"],
            )

        def market_agent(_, research_context):
            nonlocal received_market_packet
            received_market_packet = research_context
            return "market-output"

        result = self._invoke_with_fakes(
            research_builders={
                "market_agent": failed_market_research,
                "financial_agent": lambda _: FakeResearchContext("financial"),
                "risk_agent": lambda _: FakeResearchContext("risk"),
            },
            specialist_runners={
                "market_agent": market_agent,
                "financial_agent": lambda *_: "financial-output",
                "risk_agent": lambda *_: "risk-output",
            },
            memo_runner=lambda **_: "memo-output",
            report_builder=lambda *_: "report-output",
            state=self._initial_state(max_retrieval_attempts=2),
        )

        self.assertEqual(market_attempts, 2)
        self.assertEqual(
            result["retrieval_statuses"]["market_agent"],
            "exhausted",
        )
        self.assertEqual(result["retrieval_attempts"]["market_agent"], 2)
        self.assertIn('"retrieval_succeeded": false', received_market_packet)
        self.assertIn("provider unavailable", received_market_packet)
        self.assertEqual(result["report"], "report-output")
        self.assertTrue(result["workflow_warnings"])


if __name__ == "__main__":
    unittest.main()
