from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter_ns
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agents import workflow
from memory import InMemorySessionStore


class SyntheticResearchContext:
    retrieval_succeeded = True
    retrieval_errors: list[str] = []

    def __init__(self, label: str) -> None:
        self.label = label

    def to_prompt_json(self) -> str:
        return json.dumps(
            {
                "label": self.label,
                "retrieval_succeeded": True,
                "retrieval_errors": [],
            }
        )


def _latency_summary(samples_ms: list[float]) -> dict[str, float]:
    ordered = sorted(samples_ms)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    mean_ms = statistics.fmean(ordered)
    return {
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "mean_ms": round(mean_ms, 3),
        "min_ms": round(ordered[0], 3),
        "max_ms": round(ordered[-1], 3),
        "sequential_runs_per_second": round(1000 / mean_ms, 2),
    }


def _initial_state(run_id: str) -> workflow.BastionGraphState:
    return {
        "workflow_run_id": run_id,
        "session_id": "benchmark-session",
        "company_text": "Synthetic buyer and target context for orchestration timing.",
        "document_source_text": "Synthetic current-deal context.",
        "research_contexts": {},
        "document_contexts": {},
        "document_retrieval_stats": {},
        "retrieval_attempts": {},
        "retrieval_statuses": {},
        "retrieval_errors": {},
        "max_retrieval_attempts": workflow.DEFAULT_RETRIEVAL_ATTEMPTS,
        "execution_trace": [],
        "workflow_warnings": [],
    }


def benchmark_graph(iterations: int) -> dict[str, float]:
    graph = workflow.build_diligence_graph()
    research_builders = {
        agent_name: (
            lambda text, name=agent_name: SyntheticResearchContext(name)
        )
        for agent_name in workflow.SPECIALIST_OUTPUT_KEYS
    }
    samples_ms: list[float] = []

    with (
        patch.object(
            workflow,
            "run_orchestrator_agent",
            return_value=workflow.DEFAULT_PLAN,
        ),
        patch.dict(
            workflow.RESEARCH_BUILDERS,
            research_builders,
            clear=True,
        ),
        patch.dict(
            workflow.SPECIALIST_RUNNERS,
            {
                "market_agent": lambda *_: "market-output",
                "financial_agent": lambda *_: "financial-output",
                "risk_agent": lambda *_: "risk-output",
            },
            clear=True,
        ),
        patch.dict(
            workflow.SYNTHESIS_RUNNERS,
            {"memo_agent": lambda **_: "memo-output"},
            clear=True,
        ),
        patch.object(
            workflow,
            "build_report_package",
            return_value="report-output",
        ),
    ):
        for index in range(iterations):
            started_at = perf_counter_ns()
            graph.invoke(
                _initial_state(f"graph-{index}"),
                config={"recursion_limit": workflow.GRAPH_RECURSION_LIMIT},
            )
            samples_ms.append((perf_counter_ns() - started_at) / 1_000_000)

    return _latency_summary(samples_ms)


def benchmark_session_memory(iterations: int) -> dict[str, object]:
    store = InMemorySessionStore()
    session_id = "benchmark-session"
    store.get_or_create(session_id)
    write_samples_ms: list[float] = []
    read_samples_ms: list[float] = []

    for index in range(iterations):
        started_at = perf_counter_ns()
        store.add_message(
            session_id,
            "user" if index % 2 == 0 else "assistant",
            f"Synthetic benchmark message {index} " + ("x" * 160),
        )
        write_samples_ms.append((perf_counter_ns() - started_at) / 1_000_000)

    for _ in range(iterations):
        started_at = perf_counter_ns()
        store.get_recent_context(session_id)
        read_samples_ms.append((perf_counter_ns() - started_at) / 1_000_000)

    return {
        "message_write": _latency_summary(write_samples_ms),
        "bounded_recent_context_read": _latency_summary(read_samples_ms),
        "messages_present": len(store.list_messages(session_id)),
    }


def run_benchmark(iterations: int) -> dict[str, object]:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "not reported",
        },
        "iterations_per_measurement": iterations,
        "scope": (
            "Local application overhead only. Synthetic agent outputs replace "
            "Gemini, market-data, news, S3, and internet calls. Results are not "
            "end-to-end production latency."
        ),
        "graph": {"ten_node_state_graph": benchmark_graph(iterations)},
        "session_memory": benchmark_session_memory(iterations),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Bastion state-graph and session-memory overhead."
    )
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.iterations < 5:
        parser.error("--iterations must be at least 5")

    results = run_benchmark(arguments.iterations)
    rendered = json.dumps(results, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
