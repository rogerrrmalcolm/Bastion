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

AgentName = Literal["market_agent", "financial_agent", "risk_agent", "memo_agent"]

ToolName = Literal[
    "document_search",
    "financial_metric_extraction",
    "growth_rate_calculator",
    "margin_calculator",
    "runway_calculator",
    "valuation_multiple_calculator",
    "market_research",
    "live_market_data",
    "deal_market_news_search",
    "public_market_proxy_analysis",
    "risk_register",
    "citation_builder",
    "memo_synthesis",
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


class ToolAssignment(BaseModel):
    tool_name: ToolName = Field(description="Whitelisted tool assigned to the agent.")
    purpose: str = Field(description="Specific job this tool should perform.")


class AgentExecutionStep(BaseModel):
    agent_name: AgentName = Field(description="Agent responsible for this step.")
    execution_group: int = Field(
        ge=1,
        description=(
            "Steps with the same group can run in parallel. Higher groups run "
            "after lower groups complete."
        ),
    )
    objective: str = Field(description="Specific output this agent must produce.")
    context_needed: list[str] = Field(
        default_factory=list,
        description="Prior outputs or source context this step depends on.",
    )
    tools: list[ToolAssignment] = Field(
        default_factory=list,
        description="Whitelisted tools the agent should use for this step.",
    )


class OrchestrationPlan(BaseModel):
    cfo_rationale: str = Field(
        description="Brief explanation of the workflow chosen by the CFO orchestrator."
    )
    steps: list[AgentExecutionStep] = Field(
        description="Ordered plan for specialist and synthesis agents."
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


class MarketFinding(BaseModel):
    title: str = Field(description="Short market finding title.")
    detail: str = Field(description="Clear explanation for a third-party reader.")
    impact: Literal["positive", "neutral", "negative"] = Field(
        description="Expected impact on the investment thesis."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence based on available evidence."
    )
    citation: FinancialCitation | None = Field(
        default=None,
        description="Source supporting this finding.",
    )


class MarketTrend(BaseModel):
    trend: str = Field(description="Specific market trend or structural shift.")
    evidence: str = Field(
        description=(
            "Evidence, company-context support, or clearly labeled analyst inference "
            "behind the trend."
        )
    )
    affected_segments: list[str] = Field(
        default_factory=list,
        description="Customer, product, geographic, or industry segments affected.",
    )
    time_horizon: Literal["near_term", "medium_term", "long_term", "multi_year"] = Field(
        description="Expected timing of the market impact."
    )
    impact: Literal["positive", "neutral", "negative", "mixed"] = Field(
        description="Direction of impact for the company or transaction thesis."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence based on available evidence."
    )
    citation: FinancialCitation | None = Field(
        default=None,
        description="Source supporting this trend.",
    )


class MarketFactor(BaseModel):
    factor: str = Field(description="Market factor being assessed.")
    category: Literal[
        "macro",
        "geopolitical",
        "regulatory",
        "technology",
        "customer_demand",
        "supply_chain",
        "competition",
        "pricing",
        "capital_markets",
        "m_and_a",
        "other",
    ] = Field(description="Analytical category for the factor.")
    current_signal: str = Field(description="Current signal or observation.")
    thesis_impact: Literal["positive", "neutral", "negative", "mixed"] = Field(
        description="Expected effect on the investment or M&A thesis."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence based on evidence quality and market visibility."
    )
    citation: FinancialCitation | None = Field(
        default=None,
        description="Source supporting this factor.",
    )


class MarketScenario(BaseModel):
    name: str = Field(description="Short scenario name.")
    probability: Literal["low", "medium", "high"] = Field(
        description="Relative likelihood based on available evidence."
    )
    description: str = Field(description="What happens in this scenario.")
    market_impact: str = Field(description="Expected market impact.")
    m_and_a_implication: str = Field(
        description="Implication for valuation, buyer appetite, process timing, or diligence."
    )
    signposts: list[str] = Field(
        default_factory=list,
        description="Observable indicators that would make this scenario more or less likely.",
    )


class MarketResearchSource(BaseModel):
    source_type: Literal["market_data", "news_search", "web_search", "company_context"] = (
        Field(description="Type of source used in the market analysis.")
    )
    title: str = Field(description="Short source title or data point label.")
    publisher: str | None = Field(
        default=None,
        description="Publisher, endpoint, or data provider name.",
    )
    url: str | None = Field(
        default=None,
        description="Source URL when available.",
    )
    relevance: str = Field(
        description="Why this source matters for the M&A market analysis."
    )
    as_of: str | None = Field(
        default=None,
        description="Timestamp or publication date when available.",
    )


class MarketAnalysis(BaseModel):
    headline: str = Field(
        default="",
        description="Thesis-first market headline suitable for an investment committee.",
    )
    executive_summary: str = Field(description="Concise market view in plain English.")
    industry: str = Field(description="Industry or category the company operates in.")
    market_backdrop: str = Field(
        default="",
        description="Brief macro, sector, and transaction-market backdrop.",
    )
    market_position: str = Field(description="Assessment of competitive position.")
    trend_assessment: list[MarketTrend] = Field(
        default_factory=list,
        description="Core market trends and structural shifts affecting the thesis.",
    )
    key_market_factors: list[MarketFactor] = Field(
        default_factory=list,
        description=(
            "Multi-factor market assessment across macro, regulatory, technology, "
            "competition, pricing, capital markets, and M&A."
        ),
    )
    growth_drivers: list[MarketFinding] = Field(default_factory=list)
    competitive_risks: list[MarketFinding] = Field(default_factory=list)
    demand_risks: list[MarketFinding] = Field(default_factory=list)
    key_competitors: list[str] = Field(default_factory=list)
    pricing_and_margin_pressure: str = Field(
        default="",
        description="Read-through on pricing power, input costs, and margin pressure.",
    )
    capital_markets_read_through: str = Field(
        default="",
        description="Implication of public markets, financing conditions, and buyer sentiment.",
    )
    m_and_a_implications: str = Field(
        default="",
        description="Market-driven implications for M&A strategy, valuation, and timing.",
    )
    scenario_analysis: list[MarketScenario] = Field(
        default_factory=list,
        description="Base, upside, and downside market scenarios when evidence supports them.",
    )
    monitoring_signposts: list[str] = Field(
        default_factory=list,
        description="Market indicators the deal team should monitor.",
    )
    research_sources: list[MarketResearchSource] = Field(
        default_factory=list,
        description=(
            "Live market data, current news/search sources, and company-context "
            "references that informed the market analysis."
        ),
    )
    coordination_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Specific handoffs or questions for financial, risk, and memo agents."
        ),
    )
    investment_thesis_contribution: str = Field(
        description="How the market view supports or weakens the investment thesis."
    )
    missing_information: list[str] = Field(default_factory=list)
    overall_confidence: Literal["low", "medium", "high"]


class RiskItem(BaseModel):
    title: str = Field(description="Short risk title.")
    description: str = Field(description="Plain-English description of the risk.")
    category: Literal[
        "financial",
        "market",
        "legal",
        "operational",
        "technology",
        "governance",
        "execution",
        "other",
    ]
    severity: Literal["low", "medium", "high"]
    likelihood: Literal["low", "medium", "high"]
    deal_impact: str = Field(description="How this risk could affect valuation or execution.")
    mitigation: str | None = Field(default=None, description="Possible mitigation or next step.")
    citation: FinancialCitation | None = None


class RiskAnalysis(BaseModel):
    executive_summary: str = Field(description="Concise risk view in plain English.")
    top_risks: list[RiskItem] = Field(default_factory=list)
    red_flags: list[RiskItem] = Field(default_factory=list)
    diligence_priorities: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    overall_risk_rating: Literal["low", "medium", "high"]
    overall_confidence: Literal["low", "medium", "high"]


class MemoDataPoint(BaseModel):
    label: str = Field(description="Short label for the data point.")
    value: str = Field(description="Metric, finding, or conclusion.")
    source_agent: AgentName = Field(description="Agent that produced or supported the point.")
    citation: FinancialCitation | None = None


class InvestmentMemo(BaseModel):
    executive_summary: str = Field(
        description="Short narrative summary suitable for a third-party reader."
    )
    investment_thesis: str = Field(description="Narrative investment thesis.")
    recommendation: Literal["proceed", "proceed_with_caution", "pause", "decline"]
    recommendation_rationale: str = Field(description="Plain-English rationale.")
    market_view: str = Field(description="Narrative market summary.")
    financial_view: str = Field(description="Narrative financial summary.")
    risk_view: str = Field(description="Narrative risk summary.")
    key_data_points: list[MemoDataPoint] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    next_diligence_steps: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    overall_confidence: Literal["low", "medium", "high"]


class AnalyzeResponse(BaseModel):
    session_id: str
    orchestration_plan: OrchestrationPlan
    market_analysis: MarketAnalysis
    financial_analysis: FinancialAnalysis
    risk_analysis: RiskAnalysis
    investment_memo: InvestmentMemo


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
