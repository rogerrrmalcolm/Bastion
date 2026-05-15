from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor

from backend.agents.financial_agent import run_financial_agent
from backend.agents.market_agent import run_market_agent
from backend.agents.memo_agent import run_memo_agent
from backend.agents.orchestrator_agent import DEFAULT_PLAN, run_orchestrator_agent
from backend.agents.risk_agent import run_risk_agent
from backend.memory import memory_store
from backend.report_service import build_report_package
from backend.schemas import (
    AgentExecutionStep,
    AnalyzeRequest,
    AnalyzeResponse,
    FinancialAnalysis,
    MarketAnalysis,
    OrchestrationPlan,
    RiskAnalysis,
)

AgentCall = Callable[[], object]


class ParallelAgent:
    def __init__(self, agents: Mapping[str, AgentCall]) -> None:
        self.agents = agents

    def run(self) -> dict[str, object]:
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            futures = {
                name: executor.submit(agent_call)
                for name, agent_call in self.agents.items()
            }
            return {name: future.result() for name, future in futures.items()}


class SequentialAgent:
    def __init__(self, agents: Mapping[str, AgentCall]) -> None:
        self.agents = agents

    def run(self) -> dict[str, object]:
        return {name: agent_call() for name, agent_call in self.agents.items()}


SPECIALIST_RUNNERS = {
    "market_agent": run_market_agent,
    "financial_agent": run_financial_agent,
    "risk_agent": run_risk_agent,
}

CORE_SPECIALIST_SEQUENCE = ("market_agent", "financial_agent", "risk_agent")

SYNTHESIS_RUNNERS = {
    "memo_agent": run_memo_agent,
}


def _format_analyze_request_context(request: AnalyzeRequest) -> str:
    if any(
        [
            request.buyer_context,
            request.target_context,
            request.deal_context,
            request.questions,
        ]
    ):
        questions = "\n".join(
            f"{index}. {question.strip()}"
            for index, question in enumerate(request.questions, start=1)
            if question.strip()
        )
        legacy_context = request.company_text.strip() if request.company_text else ""
        return f"""
Buyer / acquirer context:
{request.buyer_context or "Not provided."}

Target company:
{request.target_context or "Not provided."}

Deal thesis / transaction context:
{request.deal_context or legacy_context or "Not provided."}

Explicit user questions:
{questions or "Use the buyer, target, and deal context to produce the core M&A comparison."}
"""

    return request.company_text or ""


def _stringify_output(output: object) -> str:
    if hasattr(output, "model_dump_json"):
        return output.model_dump_json(indent=2)
    return str(output)


def _step_for_agent(plan: OrchestrationPlan, agent_name: str) -> AgentExecutionStep:
    for step in plan.steps:
        if step.agent_name == agent_name:
            return step
    return _step_for_agent(DEFAULT_PLAN, agent_name)


def _agent_context(
    company_text: str,
    step: AgentExecutionStep,
    prior_outputs: dict[str, object],
) -> str:
    prior_context = "\n\n".join(
        f"{agent} output:\n{_stringify_output(output)}"
        for agent, output in prior_outputs.items()
    )
    return f"""
Company context:
{company_text}

CFO orchestration instruction:
{step.model_dump_json(indent=2)}

Completed prior agent outputs:
{prior_context or "None yet."}
"""


def run_planned_specialist_agents(
    company_text: str,
    plan: OrchestrationPlan,
) -> tuple[MarketAnalysis, FinancialAnalysis, RiskAnalysis]:
    outputs: dict[str, object] = {}

    for agent_name in CORE_SPECIALIST_SEQUENCE:
        step = _step_for_agent(plan, agent_name)
        outputs[agent_name] = SPECIALIST_RUNNERS[agent_name](
            _agent_context(company_text, step, outputs)
        )

    return (
        outputs["market_agent"],
        outputs["financial_agent"],
        outputs["risk_agent"],
    )


def run_investment_banking_workflow(request: AnalyzeRequest) -> AnalyzeResponse:
    session = memory_store.get_or_create(request.session_id)
    memory_context = memory_store.get_recent_context(session.session_id)
    deal_context = _format_analyze_request_context(request)
    company_text_with_memory = f"""
Conversation memory for this session:
{memory_context}

Current structured M&A deal context:
{deal_context}
"""

    memory_store.add_message(session.session_id, "user", deal_context)

    try:
        orchestration_plan = run_orchestrator_agent(company_text_with_memory)
    except Exception:
        orchestration_plan = DEFAULT_PLAN

    market_analysis, financial_analysis, risk_analysis = run_planned_specialist_agents(
        company_text_with_memory,
        orchestration_plan,
    )

    memo_step = _step_for_agent(orchestration_plan, "memo_agent")

    sequential_agent = SequentialAgent(
        {
            "memo_agent": lambda: SYNTHESIS_RUNNERS["memo_agent"](
                company_text=_agent_context(
                    company_text_with_memory,
                    memo_step,
                    {
                        "market_agent": market_analysis,
                        "financial_agent": financial_analysis,
                        "risk_agent": risk_analysis,
                    },
                ),
                market_analysis=market_analysis,
                financial_analysis=financial_analysis,
                risk_analysis=risk_analysis,
            )
        }
    )
    investment_memo = sequential_agent.run()["memo_agent"]
    report = build_report_package(
        orchestration_plan,
        market_analysis,
        financial_analysis,
        risk_analysis,
        investment_memo,
    )

    memory_store.add_message(
        session.session_id,
        "assistant",
        report.model_dump_json(indent=2),
    )

    return AnalyzeResponse(
        session_id=session.session_id,
        orchestration_plan=orchestration_plan,
        market_analysis=market_analysis,
        financial_analysis=financial_analysis,
        risk_analysis=risk_analysis,
        investment_memo=investment_memo,
        report=report,
    )
