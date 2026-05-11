import json

from backend.gemini_client import call_gemini_structured
from backend.schemas import RiskAnalysis
from backend.tools.risk_research import build_risk_research_context


def _risk_tool_context(company_text: str) -> str:
    try:
        return build_risk_research_context(company_text).to_prompt_json()
    except Exception as error:
        return json.dumps(
            {
                "error": "Risk tools failed",
                "detail": str(error),
            },
            indent=2,
        )


def run_risk_agent(company_text: str) -> RiskAnalysis:
    risk_tool_context = _risk_tool_context(company_text)

    return call_gemini_structured(
        f"""
You are Bastion's Risk Agent, supporting an investment banking diligence team.

Identify the major business, financial, legal, operational, market, and AI
governance risks. Prioritize risks that could affect valuation, diligence,
fundraising, or M&A execution. Return clear structured JSON, not prose
paragraphs outside the schema. Keep every field concise and easy for a
third-party reader to understand. Do not invent risks; list missing information
when evidence is not provided.

You have risk extraction and current news search tools. The tool packet below
contains internal risk signals from the company context plus current news search
results for regulatory, legal, cybersecurity, operating, and deal-market risks.
Prioritize risks that directly affect the M&A deal: purchase price, valuation
discounts, indemnity/escrow pressure, buyer appetite, process timing,
regulatory approvals, integration risk, and go/no-go diligence items.

When using tool output:
- cite internal_risk_signals as "provided company context"
- cite news_results with title, publisher, URL, and date where relevant
- clearly separate source-backed risks from analyst inference
- if search results are indirect or not company-specific, describe them as
  sector risk read-through rather than direct target evidence

Company context:
{company_text}

Risk extraction and news search tool packet:
{risk_tool_context}
""",
        RiskAnalysis,
    )
