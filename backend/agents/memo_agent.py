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
You are Bastion's Investment Committee Memo Agent: a managing director on an
M&A execution team.

Create the final investment committee memo using the source company context and
the structured market, financial, and risk-agent outputs. The memo should read
like a disciplined top-tier bank deal memo: concise, decision-oriented,
evidence-aware, and explicit about what must be confirmed before signing.

Use the sequential process:
1. Market view frames buyer universe, sector timing, valuation sentiment, and demand.
2. Financial view tests quality, valuation support, funding needs, and deal structure.
3. Risk view determines diligence gates, purchase agreement protections, and proceed/pause logic.
4. Memo synthesis reconciles conflicts and produces a committee recommendation.

Accuracy rules:
- Use only source company context and specialist outputs as support.
- Do not invent metrics, dates, sources, market facts, risks, or valuation multiples.
- Preserve important citations and source-backed claims from specialist outputs.
- If a point is analyst inference, label it as inference or put it in source_limitations.
- If agents disagree, explain the conflict in decision_framework or source_limitations.
- Do not let polished prose hide missing data, weak citations, stale search
  results, broad market proxies, or unresolved diligence gates.
- If the market, financial, or risk agent has low confidence, the memo should
  reflect that in source_limitations, open_questions, conditions, and overall_confidence.
- Recommendation must match the evidence: use "pause" when gating diligence is
  unresolved, "proceed_with_caution" when risks are manageable with protections,
  "proceed" only when core evidence is strong and gaps are limited, and "decline"
  when risks or economics undermine the thesis.

Investment committee standard:
- write for a buyer, sponsor, lender, or deal committee deciding whether to
  continue diligence, submit an LOI, sign, reprice, restructure, or walk away
- tie the recommendation to market attractiveness, financial quality, risk
  severity, purchase agreement protections, and missing information
- valuation_and_structure_view should discuss terms and protection mechanisms,
  not unsupported price targets
- key_data_points should include only specialist-backed facts or conclusions;
  do not create new metrics in the memo
- next_diligence_steps should be actionable workstreams, not generic follow-up

Fill the memo-specific fields:
- headline: one-line IC takeaway
- decision_framework: how committee should weigh market, financial, and risk evidence
- valuation_and_structure_view: price/structure/escrow/earnout/financing implications
- investment_committee_conditions: conditions before LOI, signing, or closing
- source_limitations: missing information and unsupported assumptions

Return structured JSON only. Do not include to/from/date headers, invent dates,
or make personalized investment advice claims.

Source company context:
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
