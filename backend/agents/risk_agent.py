from backend.gemini_client import call_gemini


def run_risk_agent(company_text: str) -> str:
    return call_gemini(
        f"""
You are a deal risk analyst supporting an investment banking team.

Identify the major business, financial, legal, operational, market, and AI
governance risks. Prioritize risks that could affect valuation, diligence,
fundraising, or M&A execution.

Company context:
{company_text}
"""
    )
