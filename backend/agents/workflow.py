import logging
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor

from agents.financial_agent import run_financial_agent
from agents.market_agent import run_market_agent
from agents.memo_agent import run_memo_agent
from agents.orchestrator_agent import DEFAULT_PLAN, run_orchestrator_agent
from agents.risk_agent import run_risk_agent
from memory import memory_store
from report_service import build_report_package
from schemas import (
    AgentExecutionStep,
    AnalyzeRequest,
    AnalyzeResponse,
    FinancialAnalysis,
    InvestmentMemo,
    MarketAnalysis,
    OrchestrationPlan,
    ReportPackage,
    RiskAnalysis,
)

AgentCall = Callable[[], object]
logger = logging.getLogger("bastion.workflow")


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


def _stringify_output(output: object, max_chars: int = 10000) -> str:
    if hasattr(output, "model_dump_json"):
        text = output.model_dump_json(indent=2)
    else:
        text = str(output)
    if len(text) > max_chars:
        return f"{text[:max_chars].rstrip()}... [truncated]"
    return text


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
    prior_block = (
        f"\nCompleted prior agent outputs:\n{prior_context}"
        if prior_context
        else ""
    )
    return f"""
Company context:
{company_text}

CFO orchestration instruction:
{step.model_dump_json(indent=2)}
{prior_block}
"""


def _workflow_memory_summary(memo: InvestmentMemo, report: ReportPackage) -> str:
    limitations = "; ".join(report.source_limitations[:3]) or "None noted"
    open_questions = "; ".join(memo.open_questions[:3]) or "None"
    return (
        f"Recommendation: {memo.recommendation}. "
        f"Summary: {memo.executive_summary} "
        f"Confidence: {memo.overall_confidence}. "
        f"Source limitations: {limitations}. "
        f"Open questions: {open_questions}."
    )


def run_planned_specialist_agents(
    company_text: str,
    plan: OrchestrationPlan,
) -> tuple[MarketAnalysis, FinancialAnalysis, RiskAnalysis]:
    outputs: dict[str, object] = {}

    for agent_name in CORE_SPECIALIST_SEQUENCE:
        step = _step_for_agent(plan, agent_name)
        logger.info("Starting specialist agent: %s", agent_name)
        outputs[agent_name] = SPECIALIST_RUNNERS[agent_name](
            _agent_context(company_text, step, outputs)
        )
        logger.info("Finished specialist agent: %s", agent_name)

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
        logger.info("Starting orchestrator agent")
        orchestration_plan = run_orchestrator_agent(company_text_with_memory)
        logger.info("Finished orchestrator agent")
    except Exception:
        logger.exception("Orchestrator failed; using default plan")
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
                    {},
                ),
                market_analysis=market_analysis,
                financial_analysis=financial_analysis,
                risk_analysis=risk_analysis,
            )
        }
    )
    logger.info("Starting memo agent")
    investment_memo = sequential_agent.run()["memo_agent"]
    logger.info("Finished memo agent")
    logger.info("Building report package")
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
        _workflow_memory_summary(investment_memo, report),
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
