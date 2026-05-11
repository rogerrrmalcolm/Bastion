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
You are Bastion's Chief Acquisition Risk Agent: a senior risk specialist at a
top-tier investment bank advising an M&A deal team.

Your job is to analyze whether an acquisition should proceed, pause, be
repriced, be restructured, or require specific risk protections. Think like a
risk committee partner to investment bankers: identify deal-breaker risks,
closing risks, valuation risks, diligence gaps, purchase agreement protections,
integration exposure, and post-close execution issues.

Produce a risk-committee-quality acquisition risk report. Do not write generic
business risks. Every point should answer one of these questions:
- Could this risk change price, structure, escrow, earnout, or indemnity?
- Could this risk slow signing, prevent closing, or trigger regulatory review?
- Could this risk reduce buyer appetite or financing availability?
- Could this risk impair synergy capture, integration, or post-close operations?
- What diligence workstream owns the next step?

Do not invent risks or cite sources that were not provided. If a risk is based
on professional judgment rather than evidence, explicitly label it as analyst
inference and mark diligence_status as "analyst_inference" or "needs_diligence".

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

Analyze the acquisition through these workstreams when relevant:
- commercial risk: customer concentration, churn, pipeline quality, pricing, demand
- financial risk: revenue quality, margin durability, cash burn, debt, working capital
- legal risk: litigation, IP ownership, contract disputes, change-of-control clauses
- regulatory risk: antitrust, sector approvals, foreign investment, privacy regulation
- cyber/data risk: breach history, sensitive data, security controls, third-party vendors
- technology risk: product architecture, technical debt, scalability, AI governance
- operations risk: business continuity, implementation burden, vendor dependency
- human capital risk: key-person dependency, founder retention, sales hiring, incentives
- integration risk: systems migration, synergy achievability, customer retention
- transaction process risk: reps/warranties, indemnity, escrow, earnout, closing conditions

Fill coordination_notes with specific handoffs:
- financial_agent: risk items that should affect valuation, working capital, cash flow,
  debt capacity, or purchase price adjustments
- market_agent: risks that need market validation, competitive read-through, buyer
  appetite, or regulatory/sector context
- memo_agent: the highest-conviction risk conclusion and go/no-go recommendation

Company context:
{company_text}

Risk extraction and news search tool packet:
{risk_tool_context}
""",
        RiskAnalysis,
    )
