from concurrent.futures import ThreadPoolExecutor

from backend.agents.financial_agent import run_financial_agent
from backend.agents.market_agent import run_market_agent
from backend.agents.memo_agent import run_memo_agent
from backend.agents.orchestrator_agent import DEFAULT_PLAN, run_orchestrator_agent
from backend.agents.risk_agent import run_risk_agent
from backend.memory import memory_store
from backend.schemas import (
    AgentExecutionStep,
    AnalyzeRequest,
    AnalyzeResponse,
    FinancialAnalysis,
    MarketAnalysis,
    OrchestrationPlan,
    RiskAnalysis,
)

SPECIALIST_RUNNERS = {
    "market_agent": run_market_agent,
    "financial_agent": run_financial_agent,
    "risk_agent": run_risk_agent,
}


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
    specialist_steps = [
        _step_for_agent(plan, agent_name) for agent_name in SPECIALIST_RUNNERS
    ]

    for execution_group in sorted({step.execution_group for step in specialist_steps}):
        group_steps = [
            step for step in specialist_steps if step.execution_group == execution_group
        ]

        with ThreadPoolExecutor(max_workers=len(group_steps)) as executor:
            futures = {
                step.agent_name: executor.submit(
                    SPECIALIST_RUNNERS[step.agent_name],
                    _agent_context(company_text, step, outputs),
                )
                for step in group_steps
            }

            for agent_name, future in futures.items():
                outputs[agent_name] = future.result()

    return (
        outputs["market_agent"],
        outputs["financial_agent"],
        outputs["risk_agent"],
    )


def run_investment_banking_workflow(request: AnalyzeRequest) -> AnalyzeResponse:
    session = memory_store.get_or_create(request.session_id)
    memory_context = memory_store.get_recent_context(session.session_id)
    company_text_with_memory = f"""
Conversation memory for this session:
{memory_context}

Current company context:
{request.company_text}
"""

    memory_store.add_message(session.session_id, "user", request.company_text)

    try:
        orchestration_plan = run_orchestrator_agent(company_text_with_memory)
    except Exception:
        orchestration_plan = DEFAULT_PLAN

    market_analysis, financial_analysis, risk_analysis = run_planned_specialist_agents(
        company_text_with_memory,
        orchestration_plan,
    )

    memo_step = _step_for_agent(orchestration_plan, "memo_agent")

    # Synthesis is intentionally sequential because it depends on specialist outputs.
    investment_memo = run_memo_agent(
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

    memory_store.add_message(
        session.session_id,
        "assistant",
        investment_memo.model_dump_json(indent=2),
    )

    return AnalyzeResponse(
        session_id=session.session_id,
        orchestration_plan=orchestration_plan,
        market_analysis=market_analysis,
        financial_analysis=financial_analysis,
        risk_analysis=risk_analysis,
        investment_memo=investment_memo,
    )
