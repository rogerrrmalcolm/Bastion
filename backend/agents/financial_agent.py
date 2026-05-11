import json

from backend.gemini_client import call_gemini_structured
from backend.schemas import FinancialAnalysis
from backend.tools.financial_research import build_financial_research_context

FINANCIAL_HIGHLIGHT_METRICS = """
Prefer annual-report-style financial highlights when present:
- income statement: revenue/net revenue, gross profit, EBITDA/operating income,
  expenses, pre-provision profit, credit losses, net income
- per share: EPS, book value per share, dividends, shares outstanding
- returns/efficiency: ROE, ROTCE, ROA, margin, overhead/efficiency ratio
- liquidity/capital: cash, debt, runway, CET1/Tier 1/total capital, leverage, LCR
- balance sheet: assets, loans, deposits, equity, working capital
- credit quality: allowances, nonperforming assets, charge-offs, default/loss rates
- valuation: enterprise value, equity value, multiples, DCF drivers, comparables
For non-bank companies, map to the closest relevant operating metrics and skip
bank-only metrics that are not supported by the source material.
"""


def _financial_tool_context(company_text: str) -> str:
    try:
        return build_financial_research_context(company_text).to_prompt_json()
    except Exception as error:
        return json.dumps(
            {
                "error": "Financial tools failed",
                "detail": str(error),
            },
            indent=2,
        )


def run_financial_agent(company_text: str) -> FinancialAnalysis:
    financial_tool_context = _financial_tool_context(company_text)

    return call_gemini_structured(
        f"""
You are Bastion's Financial Agent: a CFA-level investment banking analyst.

Your job is to produce the financial analysis that will feed the final
investment thesis and investment committee memo.

Analyze only the financial facts supported by the provided company context.
Do not invent revenue, EBITDA, margins, valuation, runway, debt, customer
concentration, or growth rates. If exact numbers are missing, say what is
missing and explain why it matters.

{FINANCIAL_HIGHLIGHT_METRICS}

You have financial extraction and calculation tools. The tool packet below
contains metrics extracted from the company context, simple deterministic
calculations, and public comp quote snapshots when explicit tickers are
provided. Use these tool outputs to ground the financial report, but still
flag anything that requires verification against source documents.

When using tool output:
- cite extracted_metrics as "provided company context"
- cite calculated_metrics by naming the formula and source metrics
- use public_comp_snapshots only as current market context, not as a valuation
  conclusion by itself
- do not create unsupported revenue, EBITDA, runway, margin, or valuation
  figures beyond what the tools or company context support

Prioritize metrics that are material to valuation, diligence, credit quality,
liquidity, capital needs, operating performance, or the investment thesis.
Mark weakly supported or irrelevant metrics as missing instead of forcing them
into the output.

Return a complete structured JSON object matching the requested schema. Use
short, decision-focused language. Every metric or finding that relies on a
source should include a citation. If no document name is available, cite
"provided company context".

Company context:
{company_text}

Financial extraction and calculation tool packet:
{financial_tool_context}
""",
        FinancialAnalysis,
    )
