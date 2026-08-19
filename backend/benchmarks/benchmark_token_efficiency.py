from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agents import financial_agent, market_agent, memo_agent, risk_agent
from agents import orchestrator_agent
from agents import workflow
from gemini_client import (
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_INSTRUCTION,
    _with_gemini_retries,
    get_gemini_client,
)
from google.genai import types
from pydantic import BaseModel
from schemas import (
    FinancialAnalysis,
    InvestmentMemo,
    MarketAnalysis,
    OrchestrationPlan,
    RiskAnalysis,
)

BENCHMARK_ID = "synthetic-buyer-target-v1"
SCENARIO_SHARED = "selective_shared_state"
SCENARIO_REPLAY = "cumulative_transcript_replay"
AGENT_ORDER = (
    "orchestrator_agent",
    "market_agent",
    "financial_agent",
    "risk_agent",
    "memo_agent",
)

COMPANY_CONTEXT = """
Buyer: Northstar Systems, a hypothetical public vertical-software company.
Target: Meridian Workflow, a hypothetical private workflow-automation vendor.
Transaction: 100% acquisition; price, financing mix, and closing date are not provided.
Geography: Buyer operates in Canada and the United States; target operates in Canada.

User-provided target facts for this synthetic benchmark only:
- FY2025 revenue was CAD 48.0 million, including CAD 39.0 million of subscription revenue.
- FY2025 adjusted EBITDA was CAD 6.0 million. The adjustment schedule was not provided.
- Cash was CAD 7.5 million and debt was CAD 3.0 million at December 31, 2025.
- The largest customer represented 14% of revenue; the top-ten concentration was not provided.
- Gross retention was 91%. Net revenue retention and cohort data were not provided.
- Management claims CAD 8-12 million of run-rate revenue synergies, but no build-up was supplied.
- The target stores customer workflow metadata and uses third-party cloud infrastructure.
- No quality-of-earnings report, customer contracts, cyber audit, litigation schedule,
  working-capital history, or purchase agreement draft has been provided.

Questions for the deal team:
1. Does the supplied evidence support continuing diligence?
2. Which valuation, financing, concentration, cyber, and integration issues could change terms?
3. Which materials are required before an LOI or signing recommendation?
""".strip()


def _fixture_json(value: object) -> str:
    return json.dumps(value, indent=2)


RESEARCH_CONTEXTS = {
    "market_agent": _fixture_json(
        {
            "retrieval_succeeded": True,
            "quote_snapshots": [],
            "news_results": [],
            "source_limitations": [
                "No target-specific market study or named public comparables were supplied.",
                "The benchmark packet intentionally contains no live claims.",
            ],
            "instruction": (
                "Use the company context as the only source-backed evidence and label "
                "all broader sector observations as analyst inference."
            ),
        }
    ),
    "financial_agent": _fixture_json(
        {
            "retrieval_succeeded": True,
            "extracted_metrics": [
                {"name": "FY2025 revenue", "value": 48.0, "unit": "CAD millions"},
                {"name": "FY2025 subscription revenue", "value": 39.0, "unit": "CAD millions"},
                {"name": "FY2025 adjusted EBITDA", "value": 6.0, "unit": "CAD millions"},
                {"name": "cash", "value": 7.5, "unit": "CAD millions"},
                {"name": "debt", "value": 3.0, "unit": "CAD millions"},
            ],
            "calculated_metrics": [
                {
                    "name": "adjusted EBITDA margin",
                    "formula": "adjusted EBITDA / revenue",
                    "value": 12.5,
                    "unit": "percent",
                }
            ],
            "public_comp_snapshots": [],
            "source_limitations": [
                "No QoE report, buyer balance sheet, valuation assumptions, or working-capital history."
            ],
        }
    ),
    "risk_agent": _fixture_json(
        {
            "retrieval_succeeded": True,
            "internal_risk_signals": [
                "Largest customer represents 14% of revenue.",
                "Customer workflow metadata is stored on third-party cloud infrastructure.",
                "Cyber audit, contracts, litigation schedule, and synergy build-up are missing.",
            ],
            "news_results": [],
            "source_limitations": [
                "No target-specific external legal, regulatory, cyber, or operating evidence was supplied."
            ],
        }
    ),
}

SPECIALIST_OUTPUTS = {
    "market_agent": _fixture_json(
        {
            "headline": "Commercial logic is plausible but not market-validated.",
            "overall_confidence": "low",
            "market_backdrop": (
                "The supplied context supports a recurring-revenue workflow-software profile, "
                "but provides no market-size, growth, competition, buyer-demand, or public-comps evidence."
            ),
            "material_trends": [
                {
                    "factor": "Subscription mix",
                    "evidence": "CAD 39.0 million of CAD 48.0 million FY2025 revenue was subscription revenue.",
                    "deal_impact": "Supports recurring-revenue diligence but does not establish durability or valuation.",
                    "source": "provided company context",
                },
                {
                    "factor": "Customer retention",
                    "evidence": "Gross retention was 91%; net revenue retention and cohort data were absent.",
                    "deal_impact": "Requires cohort and churn analysis before underwriting growth or synergies.",
                    "source": "provided company context",
                },
            ],
            "m_and_a_implications": [
                "Do not assign a market multiple without named comparables and normalized metrics.",
                "Validate channel overlap and the CAD 8-12 million revenue-synergy claim by customer cohort.",
            ],
            "buyer_target_fit": (
                "Analyst inference (not source-backed): both companies appear adjacent in vertical workflow software, "
                "but product, channel, and customer overlap were not supplied."
            ),
            "coordination_notes": {
                "financial_agent": "Test retention, concentration, and synergy assumptions against QoE and cohort data.",
                "risk_agent": "Diligence customer contracts, cloud dependencies, and synergy execution risk.",
                "memo_agent": "Treat market attractiveness and buyer appetite as unverified.",
            },
            "missing_information": [
                "Independent market size and growth study",
                "Named competitor and public-comparable set",
                "Customer cohorts, pipeline, churn, and channel-overlap analysis",
            ],
            "research_sources": ["provided company context"],
        }
    ),
    "financial_agent": _fixture_json(
        {
            "headline": "Reported profitability is positive, but QoE and buyer funding capacity are unresolved.",
            "overall_confidence": "low",
            "reported_metrics": [
                {"metric": "FY2025 revenue", "value": "CAD 48.0 million", "source": "provided company context"},
                {"metric": "FY2025 adjusted EBITDA", "value": "CAD 6.0 million", "source": "provided company context"},
                {"metric": "cash", "value": "CAD 7.5 million", "source": "provided company context"},
                {"metric": "debt", "value": "CAD 3.0 million", "source": "provided company context"},
            ],
            "calculated_metrics": [
                {
                    "metric": "adjusted EBITDA margin",
                    "value": "12.5%",
                    "formula": "CAD 6.0 million / CAD 48.0 million",
                    "source": "provided company context",
                }
            ],
            "quality_of_earnings_view": (
                "The adjustment schedule, revenue recognition, working capital, cash conversion, and one-time items "
                "must be tested in a QoE review before relying on adjusted EBITDA."
            ),
            "financing_and_debt_capacity_view": (
                "Target net cash appears positive from supplied figures, but buyer cash, debt, covenants, and "
                "financing assumptions are absent, preventing a funding-capacity conclusion."
            ),
            "valuation_and_deal_structure_implications": [
                "Use a closing net-debt and normalized-working-capital adjustment after diligence.",
                "Tie any synergy value to verified cohorts and consider contingent consideration for unproven upside.",
                "Do not recommend a price or multiple without QoE, forecasts, and a source-backed comparable set.",
            ],
            "purchase_price_adjustment_items": [
                "Cash and debt verification",
                "Normalized working-capital peg",
                "Debt-like liabilities and deferred revenue",
                "Adjustment schedule supporting reported adjusted EBITDA",
            ],
            "coordination_notes": {
                "risk_agent": "Concentration, QoE, financing, and synergy evidence remain gating workstreams.",
                "memo_agent": "Continue diligence only; economics and funding cannot yet be underwritten.",
            },
            "missing_information": [
                "QoE report and monthly financial statements",
                "Buyer balance sheet, debt covenants, and financing plan",
                "Working-capital history, cash-flow statement, forecast, and valuation assumptions",
            ],
        }
    ),
    "risk_agent": _fixture_json(
        {
            "headline": "Proceed only to bounded diligence; several risks can change price, protections, or signing readiness.",
            "overall_confidence": "low",
            "recommendation": "pause_before_loi",
            "acquisition_risk_factors": [
                {
                    "risk": "Customer concentration and contract transferability",
                    "severity": "high",
                    "source_signal": "Largest customer represents 14% of revenue; contracts were not supplied.",
                    "deal_impact": "Loss or non-consent could impair revenue and valuation.",
                    "purchase_agreement_implication": "Customer consent condition, representation, and concentration disclosure.",
                    "recommended_action": "Review top-customer contracts, renewal dates, churn, and change-of-control clauses.",
                    "diligence_owner": "commercial and legal",
                },
                {
                    "risk": "Cybersecurity and data governance",
                    "severity": "high",
                    "source_signal": "Target stores workflow metadata; no cyber audit was supplied.",
                    "deal_impact": "Unknown exposure could affect valuation, indemnity, integration, and closing readiness.",
                    "purchase_agreement_implication": "Cyber representations, special indemnity if findings warrant, and remediation covenant.",
                    "recommended_action": "Complete technical security, privacy, incident-history, and vendor reviews.",
                    "diligence_owner": "cyber, privacy, and technology",
                },
                {
                    "risk": "Unverified revenue synergies",
                    "severity": "medium",
                    "source_signal": "Management claims CAD 8-12 million with no build-up.",
                    "deal_impact": "Overstatement could weaken price support and integration planning.",
                    "purchase_agreement_implication": "Exclude unverified synergies from base price; consider contingent value only if measurable.",
                    "recommended_action": "Validate account-level cross-sell, timing, churn, costs, and ownership assumptions.",
                    "diligence_owner": "commercial, financial, and integration",
                },
            ],
            "deal_breaker_risks": [
                "Material undisclosed cyber incident or inability to transfer critical customer contracts would require pause or repricing."
            ],
            "diligence_workplan": [
                "Commercial: top-customer contracts, cohorts, churn, pipeline, and concentration.",
                "Financial: QoE, working capital, debt-like items, forecasts, and buyer financing capacity.",
                "Cyber/legal: architecture, incident history, privacy controls, litigation, IP, and change-of-control terms.",
                "Integration: product overlap, migration plan, key-person retention, and synergy build-up.",
            ],
            "coordination_notes": {
                "memo_agent": "Do not recommend LOI or signing until high-severity commercial and cyber gates are scoped and cleared."
            },
            "missing_information": [
                "Customer contracts and retention cohorts",
                "Cyber audit, data map, incident log, and vendor register",
                "Litigation, IP, employment, and regulatory materials",
            ],
        }
    ),
}

MEMO_OUTPUT = _fixture_json(
    {
        "headline": "Continue bounded diligence, but do not underwrite price or signing readiness yet.",
        "recommendation": "pause",
        "overall_confidence": "low",
        "executive_summary": (
            "Recurring revenue and positive reported adjusted EBITDA justify further work, while QoE, valuation, "
            "buyer financing, customer contracts, cyber evidence, and synergy support remain unresolved."
        ),
    }
)


@dataclass(frozen=True)
class ModelCall:
    agent_name: str
    prompt: str
    response_model: type[BaseModel]
    fixed_output: str


TokenCounter = Callable[[ModelCall], int]


def _capture_prompt(
    module: object,
    runner: Callable[..., object],
    *args: object,
    **kwargs: object,
) -> str:
    captured: list[str] = []

    def capture(prompt: str, *_: object, **__: object) -> object:
        captured.append(prompt)
        return object()

    with patch.object(module, "call_gemini_structured", side_effect=capture):
        runner(*args, **kwargs)

    if len(captured) != 1:
        raise RuntimeError(f"Expected one captured prompt, found {len(captured)}.")
    return captured[0]


def _step(agent_name: str):
    return workflow._step_for_agent(orchestrator_agent.DEFAULT_PLAN, agent_name)


def _specialist_prompt(
    agent_name: str,
    prior_outputs: dict[str, object],
) -> str:
    context = workflow._agent_context(
        COMPANY_CONTEXT,
        _step(agent_name),
        prior_outputs,
    )
    runners = {
        "market_agent": (market_agent, market_agent.run_market_agent),
        "financial_agent": (financial_agent, financial_agent.run_financial_agent),
        "risk_agent": (risk_agent, risk_agent.run_risk_agent),
    }
    module, runner = runners[agent_name]
    return _capture_prompt(module, runner, context, RESEARCH_CONTEXTS[agent_name])


def _memo_prompt(
    market_output: str,
    financial_output: str,
    risk_output: str,
) -> str:
    context = workflow._agent_context(
        COMPANY_CONTEXT,
        _step("memo_agent"),
        {},
    )
    return _capture_prompt(
        memo_agent,
        memo_agent.run_memo_agent,
        context,
        market_output,
        financial_output,
        risk_output,
    )


def _render_transcript(prior_calls: list[ModelCall]) -> str:
    turns = []
    for index, call in enumerate(prior_calls, start=1):
        turns.append(
            "\n".join(
                (
                    f"--- completed turn {index}: {call.agent_name} ---",
                    "USER REQUEST:",
                    call.prompt,
                    "ASSISTANT RESPONSE:",
                    call.fixed_output,
                )
            )
        )
    return "\n\n".join(turns)


def build_scenarios() -> dict[str, list[ModelCall]]:
    orchestrator_prompt = _capture_prompt(
        orchestrator_agent,
        orchestrator_agent.run_orchestrator_agent,
        COMPANY_CONTEXT,
    )
    plan_output = orchestrator_agent.DEFAULT_PLAN.model_dump_json(indent=2)

    shared_prompts = {
        "orchestrator_agent": orchestrator_prompt,
        "market_agent": _specialist_prompt("market_agent", {}),
        "financial_agent": _specialist_prompt(
            "financial_agent",
            {"market_agent": SPECIALIST_OUTPUTS["market_agent"]},
        ),
        "risk_agent": _specialist_prompt(
            "risk_agent",
            {
                "market_agent": SPECIALIST_OUTPUTS["market_agent"],
                "financial_agent": SPECIALIST_OUTPUTS["financial_agent"],
            },
        ),
        "memo_agent": _memo_prompt(
            SPECIALIST_OUTPUTS["market_agent"],
            SPECIALIST_OUTPUTS["financial_agent"],
            SPECIALIST_OUTPUTS["risk_agent"],
        ),
    }
    response_models: dict[str, type[BaseModel]] = {
        "orchestrator_agent": OrchestrationPlan,
        "market_agent": MarketAnalysis,
        "financial_agent": FinancialAnalysis,
        "risk_agent": RiskAnalysis,
        "memo_agent": InvestmentMemo,
    }
    outputs = {
        "orchestrator_agent": plan_output,
        **SPECIALIST_OUTPUTS,
        "memo_agent": MEMO_OUTPUT,
    }
    shared_calls = [
        ModelCall(name, shared_prompts[name], response_models[name], outputs[name])
        for name in AGENT_ORDER
    ]

    transcript_prompts = {
        "orchestrator_agent": orchestrator_prompt,
        "market_agent": _specialist_prompt("market_agent", {}),
        "financial_agent": _specialist_prompt("financial_agent", {}),
        "risk_agent": _specialist_prompt("risk_agent", {}),
        "memo_agent": _memo_prompt(
            "[Recover the market response from the transcript.]",
            "[Recover the financial response from the transcript.]",
            "[Recover the risk response from the transcript.]",
        ),
    }
    canonical_calls = [
        ModelCall(name, transcript_prompts[name], response_models[name], outputs[name])
        for name in AGENT_ORDER
    ]
    replay_calls: list[ModelCall] = []
    for index, call in enumerate(canonical_calls):
        if index == 0:
            replay_prompt = call.prompt
        else:
            replay_prompt = (
                "This agent has no shared graph state. Reconstruct the workflow "
                "context from the complete transcript below.\n\n"
                f"{_render_transcript(canonical_calls[:index])}\n\n"
                f"--- current turn: {call.agent_name} ---\n"
                f"{call.prompt}"
            )
        replay_calls.append(
            ModelCall(
                call.agent_name,
                replay_prompt,
                call.response_model,
                call.fixed_output,
            )
        )

    return {
        SCENARIO_SHARED: shared_calls,
        SCENARIO_REPLAY: replay_calls,
    }


def gemini_token_counter(model: str = DEFAULT_MODEL) -> TokenCounter:
    def count(call: ModelCall) -> int:
        config = types.CountTokensConfig(
            system_instruction=DEFAULT_SYSTEM_INSTRUCTION,
            generation_config=types.GenerationConfig(
                response_mime_type="application/json",
                response_json_schema=call.response_model.model_json_schema(),
            ),
        )
        response = _with_gemini_retries(
            lambda: get_gemini_client().models.count_tokens(
                model=model,
                contents=call.prompt,
                config=config,
            )
        )
        if response.total_tokens is None:
            raise RuntimeError("Gemini countTokens returned no total_tokens value.")
        return int(response.total_tokens)

    return count


def estimated_token_counter(call: ModelCall) -> int:
    request_material = "\n".join(
        (
            DEFAULT_SYSTEM_INSTRUCTION,
            call.prompt,
            json.dumps(
                call.response_model.model_json_schema(),
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    )
    return math.ceil(len(request_material.encode("utf-8")) / 4)


def _measure_scenario(
    calls: list[ModelCall],
    counter: TokenCounter,
) -> dict[str, object]:
    per_call: dict[str, dict[str, int]] = {}
    for call in calls:
        per_call[call.agent_name] = {
            "input_tokens": counter(call),
            "prompt_characters": len(call.prompt),
        }
    return {
        "model_calls": len(calls),
        "total_input_tokens": sum(item["input_tokens"] for item in per_call.values()),
        "total_prompt_characters": sum(
            item["prompt_characters"] for item in per_call.values()
        ),
        "per_call": per_call,
    }


def run_benchmark(
    counter: TokenCounter,
    *,
    model: str = DEFAULT_MODEL,
    counter_name: str = "Injected token counter",
    exact_count: bool = False,
) -> dict[str, object]:
    scenarios = build_scenarios()
    measured = {
        name: _measure_scenario(calls, counter)
        for name, calls in scenarios.items()
    }
    shared_tokens = int(measured[SCENARIO_SHARED]["total_input_tokens"])
    replay_tokens = int(measured[SCENARIO_REPLAY]["total_input_tokens"])
    tokens_saved = replay_tokens - shared_tokens
    reduction = (tokens_saved / replay_tokens * 100) if replay_tokens else 0.0

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "benchmark_id": BENCHMARK_ID,
        "model": model,
        "token_counter": counter_name,
        "exact_model_token_count": exact_count,
        "scope": (
            "Input-token benchmark for five model calls. Counts include Bastion's system "
            "instruction and each structured-response JSON schema. Fixed output "
            "fixtures are replayed as context where required but output-generation "
            "tokens, research API traffic, retries, and deterministic report building "
            "are outside the measured total."
        ),
        "methodology": {
            SCENARIO_SHARED: (
                "Current Bastion topology. LangGraph state projects only the plan step "
                "and required upstream specialist outputs into each downstream prompt."
            ),
            SCENARIO_REPLAY: (
                "Counterfactual stateless chat topology. Every downstream call receives "
                "the complete prior user/assistant transcript to reconstruct workflow context."
            ),
            "controls": (
                "Both scenarios use the same model, system instruction, response schemas, "
                "five-call sequence, company context, research packets, and fixed outputs."
            ),
            "interpretation": (
                "This isolates selective state projection versus cumulative transcript "
                "replay. It does not claim that LangGraph alone reduces tokens, and it is "
                "not a comparison against every possible hand-built stateless orchestrator."
            ),
        },
        "fixture": {
            "company_context_characters": len(COMPANY_CONTEXT),
            "research_context_characters": {
                name: len(value) for name, value in RESEARCH_CONTEXTS.items()
            },
            "fixed_output_characters": {
                "orchestrator_agent": len(
                    orchestrator_agent.DEFAULT_PLAN.model_dump_json(indent=2)
                ),
                **{
                    name: len(value) for name, value in SPECIALIST_OUTPUTS.items()
                },
                "memo_agent": len(MEMO_OUTPUT),
            },
        },
        "scenarios": measured,
        "comparison": {
            "input_tokens_saved": tokens_saved,
            "input_token_reduction_percent": round(reduction, 2),
            "shared_state_uses_percent_of_replay": round(
                shared_tokens / replay_tokens * 100 if replay_tokens else 0.0,
                2,
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark Bastion's selective LangGraph state handoffs against "
            "cumulative transcript replay using Gemini countTokens."
        )
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--counter",
        choices=("gemini", "estimate"),
        default="gemini",
        help=(
            "Use Vertex AI countTokens for exact counts, or the deterministic "
            "ceil(UTF-8 bytes / 4) estimator for offline comparisons."
        ),
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    if arguments.counter == "gemini":
        counter = gemini_token_counter(arguments.model)
        counter_name = "Google Vertex AI Gemini countTokens"
        exact_count = True
    else:
        counter = estimated_token_counter
        counter_name = "Deterministic estimate: ceil(UTF-8 request bytes / 4)"
        exact_count = False

    results = run_benchmark(
        counter,
        model=arguments.model,
        counter_name=counter_name,
        exact_count=exact_count,
    )
    rendered = json.dumps(results, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
