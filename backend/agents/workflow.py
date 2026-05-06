from backend.agents.financial_agent import run_financial_agent
from backend.agents.market_agent import run_market_agent
from backend.agents.memo_agent import run_memo_agent
from backend.agents.risk_agent import run_risk_agent
from backend.schemas import AnalyzeRequest, AnalyzeResponse


def run_investment_banking_workflow(request: AnalyzeRequest) -> AnalyzeResponse:
    market_analysis = run_market_agent(request.company_text)
    financial_analysis = run_financial_agent(request.company_text)
    risk_analysis = run_risk_agent(request.company_text)

    investment_memo = run_memo_agent(
        company_text=request.company_text,
        market_analysis=market_analysis,
        financial_analysis=financial_analysis,
        risk_analysis=risk_analysis,
    )

    return AnalyzeResponse(
        market_analysis=market_analysis,
        financial_analysis=financial_analysis,
        risk_analysis=risk_analysis,
        investment_memo=investment_memo,
    )
