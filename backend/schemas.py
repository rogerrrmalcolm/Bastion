from typing import Literal

from pydantic import BaseModel, Field

MetricCategory = Literal[
    "income_statement",
    "per_share",
    "returns",
    "efficiency",
    "liquidity_capital",
    "balance_sheet",
    "credit_quality",
    "growth",
    "valuation",
    "other",
]


class AnalyzeRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Existing session id. If omitted, a new session is created.",
    )
    company_text: str = Field(
        min_length=20,
        description="Company, market, financial, or deal context to analyze.",
    )


class FinancialCitation(BaseModel):
    source: str = Field(
        description=(
            "Document, section, or provided context that supports the finding. "
            "Use 'provided company context' when no document name is available."
        )
    )
    page: int | None = Field(
        default=None,
        description="Page number when the source is a paginated document.",
    )
    excerpt: str | None = Field(
        default=None,
        description="Short supporting excerpt or data point, if available.",
    )


class FinancialMetric(BaseModel):
    name: str = Field(description="Metric name, such as Revenue, EBITDA, or Gross Margin.")
    category: MetricCategory = Field(
        description="Financial highlight category for frontend grouping."
    )
    value: str = Field(description="Reported or calculated metric value.")
    period: str | None = Field(
        default=None,
        description="Relevant fiscal period, quarter, month, or LTM window.",
    )
    comparison: str | None = Field(
        default=None,
        description="Prior-period comparison, growth rate, or trend when available.",
    )
    interpretation: str = Field(
        description="Deal-relevant explanation of what the metric implies."
    )
    relevance: Literal["core", "supporting", "low"] = Field(
        description="How important this metric is to the financial thesis."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence based on source quality and completeness."
    )
    citation: FinancialCitation | None = Field(
        default=None,
        description="Source supporting this metric.",
    )


class FinancialFinding(BaseModel):
    title: str = Field(description="Short finding title.")
    detail: str = Field(description="Decision-focused explanation of the finding.")
    severity: Literal["low", "medium", "high"] = Field(
        description="Potential impact on valuation or transaction execution."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence based on available financial evidence."
    )
    citation: FinancialCitation | None = Field(
        default=None,
        description="Source supporting this finding.",
    )


class FinancialAnalysis(BaseModel):
    executive_summary: str = Field(
        description="Concise CFO/CFA-style summary of the company's financial profile."
    )
    investment_thesis_contribution: str = Field(
        description=(
            "How the financial analysis supports, weakens, or conditions the "
            "investment thesis."
        )
    )
    revenue_quality: str = Field(
        description="Assessment of revenue growth, recurrence, concentration, and durability."
    )
    profitability_and_margins: str = Field(
        description="Assessment of gross margin, EBITDA, operating leverage, and margin trend."
    )
    cost_structure: str = Field(
        description="Assessment of fixed versus variable costs and scalability."
    )
    cash_flow_and_working_capital: str = Field(
        description="Assessment of cash conversion, working capital needs, and burn."
    )
    capital_structure_and_liquidity: str = Field(
        description="Assessment of debt, runway, liquidity, and financing needs."
    )
    valuation_view: str = Field(
        description="Financial view on valuation support, pressure points, and needed comps."
    )
    key_metrics: list[FinancialMetric] = Field(
        default_factory=list,
        description="Material reported or calculated financial metrics.",
    )
    financial_strengths: list[FinancialFinding] = Field(
        default_factory=list,
        description="Financial attributes that support the deal thesis.",
    )
    financial_concerns: list[FinancialFinding] = Field(
        default_factory=list,
        description="Financial weaknesses, diligence concerns, or pressure points.",
    )
    red_flags: list[FinancialFinding] = Field(
        default_factory=list,
        description="High-priority financial issues that may affect valuation or execution.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Financial documents or data needed before making firmer conclusions.",
    )
    diligence_questions: list[str] = Field(
        default_factory=list,
        description="Specific follow-up questions for the company or deal team.",
    )
    overall_confidence: Literal["low", "medium", "high"] = Field(
        description="Overall confidence in the financial analysis."
    )


class AnalyzeResponse(BaseModel):
    session_id: str
    market_analysis: str
    financial_analysis: FinancialAnalysis
    risk_analysis: str
    investment_memo: str


class ChatRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Existing session id. If omitted, a new session is created.",
    )
    message: str = Field(
        min_length=1,
        description="User prompt for the investment banking assistant.",
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str


class MemoryMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str


class SessionMemoryResponse(BaseModel):
    session_id: str
    messages: list[MemoryMessageResponse]
