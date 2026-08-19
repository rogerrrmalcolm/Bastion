import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks import benchmark_token_efficiency as benchmark


class TokenEfficiencyBenchmarkTests(unittest.TestCase):
    @staticmethod
    def _deterministic_counter(call: benchmark.ModelCall) -> int:
        return len(call.prompt)

    def test_scenarios_keep_the_same_call_order_and_response_models(self) -> None:
        scenarios = benchmark.build_scenarios()
        shared = scenarios[benchmark.SCENARIO_SHARED]
        replay = scenarios[benchmark.SCENARIO_REPLAY]

        self.assertEqual(
            [call.agent_name for call in shared],
            list(benchmark.AGENT_ORDER),
        )
        self.assertEqual(
            [call.agent_name for call in replay],
            list(benchmark.AGENT_ORDER),
        )
        self.assertEqual(
            [call.response_model for call in shared],
            [call.response_model for call in replay],
        )
        self.assertEqual(
            [call.fixed_output for call in shared],
            [call.fixed_output for call in replay],
        )

    def test_replay_uses_more_context_for_every_downstream_call(self) -> None:
        scenarios = benchmark.build_scenarios()
        shared = scenarios[benchmark.SCENARIO_SHARED]
        replay = scenarios[benchmark.SCENARIO_REPLAY]

        self.assertEqual(len(shared[0].prompt), len(replay[0].prompt))
        for shared_call, replay_call in zip(shared[1:], replay[1:], strict=True):
            self.assertGreater(len(replay_call.prompt), len(shared_call.prompt))

    def test_result_reports_savings_without_changing_call_count(self) -> None:
        result = benchmark.run_benchmark(self._deterministic_counter)
        shared = result["scenarios"][benchmark.SCENARIO_SHARED]
        replay = result["scenarios"][benchmark.SCENARIO_REPLAY]

        self.assertEqual(shared["model_calls"], replay["model_calls"])
        self.assertGreater(
            replay["total_input_tokens"],
            shared["total_input_tokens"],
        )
        self.assertEqual(
            result["comparison"]["input_tokens_saved"],
            replay["total_input_tokens"] - shared["total_input_tokens"],
        )
        self.assertGreater(
            result["comparison"]["input_token_reduction_percent"],
            0,
        )

    def test_offline_estimator_includes_schema_and_system_instruction(self) -> None:
        call = benchmark.build_scenarios()[benchmark.SCENARIO_SHARED][0]
        prompt_only_estimate = len(call.prompt.encode("utf-8")) // 4

        self.assertGreater(
            benchmark.estimated_token_counter(call),
            prompt_only_estimate,
        )


if __name__ == "__main__":
    unittest.main()
