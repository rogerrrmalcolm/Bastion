from backend.gemini_client import call_gemini_structured
from backend.schemas import (
    FinancialAnalysis,
    InvestmentMemo,
    MarketAnalysis,
    RiskAnalysis,
)


def _to_json_context(value: object) -> str:
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json(indent=2)
    return str(value)


def run_memo_agent(
    company_text: str,
    market_analysis: MarketAnalysis | str,
    financial_analysis: FinancialAnalysis | str,
    risk_analysis: RiskAnalysis | str,
) -> InvestmentMemo:
    return call_gemini_structured(
        f"""
You are a managing director at an investment bank.

Create the final investment memo using the source company context and structured
specialist outputs. The final memo should mix concise narrative sentences with
clear data fields. Return structured JSON only. Do not include to/from/date
headers, invent dates, or make personalized investment advice claims.

Company context:
{company_text}

Market analyst structured output:
{_to_json_context(market_analysis)}

Financial analyst structured output:
{_to_json_context(financial_analysis)}

Risk analyst structured output:
{_to_json_context(risk_analysis)}
""",
        InvestmentMemo,
    )
