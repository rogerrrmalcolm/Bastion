from backend.gemini_client import call_gemini


def run_market_agent(company_text: str) -> str:
    return call_gemini(
        f"""
You are a market analyst supporting an investment banking team.

Analyze the company's market, industry position, competitors, growth drivers,
and demand risks. Keep the output concise and decision-focused.

Company context:
{company_text}
"""
    )
