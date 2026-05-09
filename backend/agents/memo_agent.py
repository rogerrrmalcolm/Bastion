from backend.gemini_client import call_gemini
from backend.schemas import FinancialAnalysis


def run_memo_agent(
    company_text: str,
    market_analysis: str,
    financial_analysis: FinancialAnalysis | str,
    risk_analysis: str,
) -> str:
    if isinstance(financial_analysis, FinancialAnalysis):
        financial_analysis_context = financial_analysis.model_dump_json(indent=2)
    else:
        financial_analysis_context = financial_analysis

    return call_gemini(
        f"""
You are a managing director at an investment bank.

Create a concise investment banking memo using the source company context and
the specialist agent outputs. Include: overview, market view, financial view,
key risks, recommendation, and next diligence steps. Do not include to/from/date
headers or invent dates. Do not make personalized investment advice claims.

Company context:
{company_text}

Market analyst output:
{market_analysis}

Financial analyst structured output:
{financial_analysis_context}

Risk analyst output:
{risk_analysis}
"""
    )
