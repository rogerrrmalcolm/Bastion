from backend.gemini_client import call_gemini


def run_memo_agent(
    company_text: str,
    market_analysis: str,
    financial_analysis: str,
    risk_analysis: str,
) -> str:
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

Financial analyst output:
{financial_analysis}

Risk analyst output:
{risk_analysis}
"""
    )
