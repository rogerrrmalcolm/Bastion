from backend.gemini_client import call_gemini


def run_financial_agent(company_text: str) -> str:
    return call_gemini(
        f"""
You are a financial analyst supporting an investment banking team.

Analyze revenue quality, margin profile, cost structure, capital needs,
valuation signals, and financial strengths or weaknesses. If exact numbers
are missing, state what information is needed instead of inventing data.

Company context:
{company_text}
"""
    )
