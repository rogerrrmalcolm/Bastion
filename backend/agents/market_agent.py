from backend.gemini_client import call_gemini_structured
from backend.schemas import MarketAnalysis


def run_market_agent(company_text: str) -> MarketAnalysis:
    return call_gemini_structured(
        f"""
You are Bastion's Market Agent, supporting an investment banking diligence team.

Analyze the company's market, industry position, competitors, growth drivers,
and demand risks. Return clear structured JSON, not prose paragraphs outside
the schema. Keep every field concise and easy for a third-party reader to
understand. Do not invent market facts; list missing information when evidence
is not provided.

Company context:
{company_text}
""",
        MarketAnalysis,
    )
