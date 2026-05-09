from concurrent.futures import ThreadPoolExecutor

from backend.agents.financial_agent import run_financial_agent
from backend.agents.market_agent import run_market_agent
from backend.agents.memo_agent import run_memo_agent
from backend.agents.risk_agent import run_risk_agent
from backend.memory import memory_store
from backend.schemas import AnalyzeRequest, AnalyzeResponse, FinancialAnalysis


def run_specialist_agents(company_text: str) -> tuple[str, FinancialAnalysis, str]:
    with ThreadPoolExecutor(max_workers=3) as executor:
        market_future = executor.submit(run_market_agent, company_text)
        financial_future = executor.submit(run_financial_agent, company_text)
        risk_future = executor.submit(run_risk_agent, company_text)

        return (
            market_future.result(),
            financial_future.result(),
            risk_future.result(),
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

    market_analysis, financial_analysis, risk_analysis = run_specialist_agents(
        company_text_with_memory
    )

    # Synthesis is intentionally sequential because it depends on specialist outputs.
    investment_memo = run_memo_agent(
        company_text=company_text_with_memory,
        market_analysis=market_analysis,
        financial_analysis=financial_analysis,
        risk_analysis=risk_analysis,
    )

    memory_store.add_message(session.session_id, "assistant", investment_memo)

    return AnalyzeResponse(
        session_id=session.session_id,
        market_analysis=market_analysis,
        financial_analysis=financial_analysis,
        risk_analysis=risk_analysis,
        investment_memo=investment_memo,
    )
