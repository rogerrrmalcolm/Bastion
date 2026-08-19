from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
    "quality_of_earnings_review",
    "working_capital_analysis",
    "purchase_price_adjustment_analysis",
    "debt_capacity_screen",
    "market_research",
    "live_market_data",
    "deal_market_news_search",
    "public_market_proxy_analysis",
    "risk_register",
    "acquisition_risk_matrix",
    "regulatory_risk_search",
    "cyber_diligence_screen",
    "integration_risk_assessment",
    "purchase_agreement_risk_mapper",
    "citation_builder",
    "memo_synthesis",
    "investment_committee_memo_builder",
    "evidence_reconciliation",
]


class AnalyzeRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Existing session id. If omitted, a new session is created.",
    )
    company_text: str | None = Field(
        default=None,
        description=(
            "Legacy single-field company, market, financial, or deal context. "
            "Prefer buyer_context, target_context, deal_context, and questions."
        ),
    )
    buyer_context: str | None = Field(
        default=None,
        description="Acquirer/buyer strategy, operating profile, financing capacity, and rationale.",
    )
    target_context: str | None = Field(
        default=None,
        description="Target company profile, financials, market position, risks, and diligence data.",
    )
    deal_context: str | None = Field(
        default=None,
        description="Transaction thesis, structure, valuation assumptions, and deal-specific context.",
    )
    questions: list[str] = Field(
        default_factory=list,
        description="Explicit user questions the final memo must answer directly.",
    )

    @model_validator(mode="after")
    def require_analyzable_context(self) -> "AnalyzeRequest":
        context_parts = [
            self.company_text,
            self.buyer_context,
            self.target_context,
            self.deal_context,
            "\n".join(self.questions),
        ]
        context_length = len("\n".join(part.strip() for part in context_parts if part))
        if context_length < 20:
            raise ValueError(
                "Provide at least 20 characters of company or deal context to analyze."
            )
        return self


class ToolAssignment(BaseModel):
    tool_name: ToolName = Field(description="Whitelisted tool assigned to the agent.")
    purpose: str = Field(description="Specific job this tool should perform.")


class AgentExecutionStep(BaseModel):
    agent_name: AgentName = Field(description="Agent responsible for this step.")
    execution_group: int = Field(
        ge=1,
        description=(
            "Ordering group for the diligence plan. Use distinct groups for "
            "Bastion's core sequence: market, financial, risk, then memo."
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
    headline: str = Field(
        default="",
        description="Investment-committee-ready financial headline.",
    )
    executive_summary: str = Field(
        description="Concise CFO/CFA-style summary of the company's financial profile."
    )
    m_and_a_financial_assessment: str = Field(
        default="",
        description="How the financial profile affects acquisition attractiveness and process risk.",
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
    quality_of_earnings_view: str = Field(
        default="",
        description="View on earnings quality, normalization needs, and source reliability.",
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
    financing_and_debt_capacity_view: str = Field(
        default="",
        description="Read-through for leverage capacity, financing risk, and buyer funding needs.",
    )
    purchase_price_adjustment_items: list[str] = Field(
        default_factory=list,
        description="Potential net debt, working capital, cash, debt-like item, or QoE adjustments.",
    )
    valuation_and_deal_structure_implications: list[str] = Field(
        default_factory=list,
        description="Implications for price, multiple, earnout, seller note, rollover, or escrow.",
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
    coordination_notes: list[str] = Field(
        default_factory=list,
        description="Specific handoffs for market, risk, and memo agents.",
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
        "commercial",
        "financial",
        "market",
        "legal",
        "regulatory",
        "tax",
        "operational",
        "technology",
        "cybersecurity",
        "data_privacy",
        "integration",
        "human_capital",
        "governance",
        "execution",
        "reputation",
        "transaction_process",
        "other",
    ]
    severity: Literal["low", "medium", "high"]
    likelihood: Literal["low", "medium", "high"]
    deal_impact: str = Field(description="How this risk could affect valuation or execution.")
    mitigation: str | None = Field(default=None, description="Possible mitigation or next step.")
    citation: FinancialCitation | None = None


class AcquisitionRiskFactor(BaseModel):
    risk_area: Literal[
        "commercial",
        "financial",
        "legal",
        "regulatory",
        "tax",
        "technology",
        "cybersecurity",
        "data_privacy",
        "operations",
        "integration",
        "human_capital",
        "governance",
        "financing",
        "reputation",
        "transaction_process",
        "other",
    ] = Field(description="Primary acquisition-risk area.")
    finding: str = Field(description="Specific risk finding.")
    source_signal: str = Field(
        description=(
            "Source-backed signal, tool result, or explicitly labeled analyst inference."
        )
    )
    severity: Literal["low", "medium", "high"]
    likelihood: Literal["low", "medium", "high"]
    diligence_status: Literal["source_backed", "analyst_inference", "needs_diligence"] = (
        Field(description="Evidence status for the risk.")
    )
    deal_impact: str = Field(
        description="Effect on valuation, process certainty, buyer appetite, or closing risk."
    )
    purchase_agreement_implication: str = Field(
        description="Likely impact on reps, warranties, covenants, indemnity, escrow, or conditions."
    )
    recommended_action: str = Field(description="Concrete diligence or mitigation action.")
    diligence_owner: Literal[
        "commercial",
        "financial",
        "legal",
        "tax",
        "regulatory",
        "cyber",
        "technology",
        "operations",
        "human_capital",
        "management",
        "deal_team",
    ] = Field(description="Workstream that should own follow-up.")
    citation: FinancialCitation | None = None


class DiligenceWorkstream(BaseModel):
    workstream: Literal[
        "commercial",
        "financial",
        "legal",
        "tax",
        "regulatory",
        "cyber",
        "technology",
        "operations",
        "human_capital",
        "integration",
        "management",
        "transaction_process",
    ] = Field(description="Diligence workstream.")
    priority: Literal["low", "medium", "high"]
    scope: str = Field(description="What this workstream must test.")
    key_questions: list[str] = Field(default_factory=list)
    required_materials: list[str] = Field(default_factory=list)
    gating_decision: str = Field(
        description="What decision this diligence workstream should enable."
    )


class RiskMitigationAction(BaseModel):
    action: str = Field(description="Specific mitigation or deal-protection action.")
    owner: Literal[
        "buyer",
        "seller",
        "legal_counsel",
        "financial_advisor",
        "management",
        "deal_team",
        "third_party_specialist",
    ] = Field(description="Party best positioned to own the action.")
    timing: Literal["pre_loi", "confirmatory_diligence", "signing", "pre_close", "post_close"]
    priority: Literal["low", "medium", "high"]
    expected_effect: str = Field(description="How the action reduces risk.")


class AcquisitionRiskScenario(BaseModel):
    name: str = Field(description="Short scenario name.")
    probability: Literal["low", "medium", "high"]
    trigger_events: list[str] = Field(default_factory=list)
    downside_case: str = Field(description="What goes wrong in this scenario.")
    deal_impact: str = Field(description="Impact on valuation, timing, closing, or integration.")
    mitigation_response: str = Field(description="How the deal team should respond.")


class RiskResearchSource(BaseModel):
    source_type: Literal["company_context", "internal_risk_signal", "news_search"] = Field(
        description="Type of risk source used."
    )
    title: str = Field(description="Short source or risk-signal title.")
    publisher: str | None = Field(default=None)
    url: str | None = Field(default=None)
    relevance: str = Field(description="Why this source matters to acquisition risk.")
    as_of: str | None = Field(default=None)


class RiskAnalysis(BaseModel):
    headline: str = Field(
        default="",
        description="Board-level acquisition-risk headline.",
    )
    executive_summary: str = Field(description="Concise risk view in plain English.")
    acquisition_risk_summary: str = Field(
        default="",
        description="Overall acquisition risk framing for buyer, seller, and deal team.",
    )
    overall_deal_risk_score: Literal["low", "medium", "high", "critical"] = Field(
        default="medium",
        description="Overall acquisition risk score before mitigation.",
    )
    top_risks: list[RiskItem] = Field(default_factory=list)
    red_flags: list[RiskItem] = Field(default_factory=list)
    deal_breaker_risks: list[RiskItem] = Field(
        default_factory=list,
        description="Risks that could justify pausing, repricing, or abandoning the deal.",
    )
    acquisition_risk_factors: list[AcquisitionRiskFactor] = Field(
        default_factory=list,
        description="Detailed acquisition risk matrix for the deal team.",
    )
    diligence_priorities: list[str] = Field(default_factory=list)
    diligence_workplan: list[DiligenceWorkstream] = Field(
        default_factory=list,
        description="Priority diligence workstreams and required materials.",
    )
    mitigation_plan: list[RiskMitigationAction] = Field(
        default_factory=list,
        description="Deal protections and mitigations to pursue.",
    )
    risk_scenarios: list[AcquisitionRiskScenario] = Field(
        default_factory=list,
        description="Base/downside risk scenarios for acquisition planning.",
    )
    purchase_agreement_implications: list[str] = Field(
        default_factory=list,
        description="Expected impacts on reps, warranties, covenants, indemnity, escrow, or closing conditions.",
    )
    valuation_and_terms_implications: list[str] = Field(
        default_factory=list,
        description="How risk should affect price, structure, earnout, escrow, or financing terms.",
    )
    integration_risk_view: str = Field(
        default="",
        description="Risk view on post-close integration, operating continuity, and synergy capture.",
    )
    regulatory_approval_view: str = Field(
        default="",
        description="Risk view on regulatory approvals, antitrust, sector regulation, or foreign investment review.",
    )
    cyber_data_privacy_view: str = Field(
        default="",
        description="Risk view on cybersecurity, data privacy, and sensitive data handling.",
    )
    management_governance_view: str = Field(
        default="",
        description="Risk view on management quality, controls, governance, and key-person dependency.",
    )
    risk_sources: list[RiskResearchSource] = Field(
        default_factory=list,
        description="Risk sources used from company context and live news/search tools.",
    )
    coordination_notes: list[str] = Field(
        default_factory=list,
        description="Handoffs for financial, market, and memo agents.",
    )
    missing_information: list[str] = Field(default_factory=list)
    overall_risk_rating: Literal["low", "medium", "high"]
    overall_confidence: Literal["low", "medium", "high"]


class MemoDataPoint(BaseModel):
    label: str = Field(description="Short label for the data point.")
    value: str = Field(description="Metric, finding, or conclusion.")
    source_agent: AgentName = Field(description="Agent that produced or supported the point.")
    citation: FinancialCitation | None = None


class MemoQuestionAnswer(BaseModel):
    question: str = Field(description="Explicit user question or requested analysis item.")
    answer: str = Field(
        description=(
            "Direct answer to the user question using available agent outputs. "
            "If evidence is incomplete, answer what can be answered and state the exact gap."
        )
    )
    evidence_status: Literal["answered", "partial", "insufficient_evidence"] = Field(
        description="Whether the available evidence fully answers the question."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence in this specific answer."
    )
    source_agents: list[AgentName] = Field(
        default_factory=list,
        description="Agents whose outputs support the answer.",
    )


class ReportCitation(BaseModel):
    agent_name: AgentName = Field(description="Agent that supplied this source.")
    source_type: Literal[
        "company_context",
        "document",
        "market_data",
        "news_search",
        "web_search",
        "internal_risk_signal",
        "calculated_metric",
        "agent_output",
        "analyst_inference",
    ] = Field(description="Normalized source category.")
    title: str = Field(description="Short source title or evidence label.")
    source: str = Field(description="Document, endpoint, context, or agent output name.")
    relevance: str = Field(description="How this source supports the final report.")
    publisher: str | None = Field(default=None)
    url: str | None = Field(default=None)
    page: int | None = Field(default=None)
    excerpt: str | None = Field(default=None)
    as_of: str | None = Field(default=None)


class AgentContribution(BaseModel):
    agent_name: AgentName
    label: str = Field(description="Human-readable agent label.")
    summary: str = Field(description="What this agent contributed to the final solution.")
    provides_to_final_solution: list[str] = Field(
        default_factory=list,
        description="Specific memo or decision components this agent supports.",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Highest-signal findings surfaced by this agent.",
    )
    citations: list[ReportCitation] = Field(
        default_factory=list,
        description="Normalized citations used by this agent.",
    )
    confidence: Literal["low", "medium", "high"] | None = None


class ReportSection(BaseModel):
    title: str
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)
    source_agents: list[AgentName] = Field(default_factory=list)
    citations: list[ReportCitation] = Field(default_factory=list)


class ReportPackage(BaseModel):
    title: str = Field(description="Reader-facing report title.")
    recommendation: str = Field(description="Normalized recommendation label.")
    executive_summary: str = Field(description="Decision-oriented summary.")
    agent_contributions: list[AgentContribution] = Field(
        default_factory=list,
        description="Agent-by-agent contribution and citation map.",
    )
    sections: list[ReportSection] = Field(
        default_factory=list,
        description="Structured report sections for the frontend report service.",
    )
    source_register: list[ReportCitation] = Field(
        default_factory=list,
        description="Deduplicated source register across all agents.",
    )
    source_limitations: list[str] = Field(default_factory=list)


class InvestmentMemo(BaseModel):
    headline: str = Field(
        default="",
        description="One-line investment committee headline.",
    )
    executive_summary: str = Field(
        description="Short narrative summary suitable for a third-party reader."
    )
    investment_thesis: str = Field(description="Narrative investment thesis.")
    buyer_target_fit_view: str = Field(
        default="",
        description=(
            "Direct comparison of buyer/acquirer fit with the target, including "
            "strategic rationale, synergy logic, integration fit, and key mismatch risks."
        ),
    )
    recommendation: Literal["proceed", "proceed_with_caution", "pause", "decline"]
    recommendation_rationale: str = Field(description="Plain-English rationale.")
    decision_framework: str = Field(
        default="",
        description="How the committee should weigh market, financial, and risk outputs.",
    )
    market_view: str = Field(description="Narrative market summary.")
    financial_view: str = Field(description="Narrative financial summary.")
    risk_view: str = Field(description="Narrative risk summary.")
    valuation_and_structure_view: str = Field(
        default="",
        description="View on valuation, structure, earnout, escrow, rollover, or financing terms.",
    )
    question_answers: list[MemoQuestionAnswer] = Field(
        default_factory=list,
        description=(
            "Direct answers to explicit user questions from the original prompt, "
            "kept separate from the deal team's open diligence questions."
        ),
    )
    key_data_points: list[MemoDataPoint] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    investment_committee_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that should be satisfied before proceed or signing.",
    )
    next_diligence_steps: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    source_limitations: list[str] = Field(
        default_factory=list,
        description="Important evidence gaps, unsupported inferences, and source limitations.",
    )
    overall_confidence: Literal["low", "medium", "high"]


class WorkflowDiagnostics(BaseModel):
    workflow_run_id: str = Field(
        description="Unique correlation id for this isolated analysis run."
    )
    state_scope: Literal["single_run"] = Field(
        default="single_run",
        description=(
            "LangGraph state is shared by nodes during one workflow invocation."
        ),
    )
    checkpointing_enabled: bool = Field(
        default=False,
        description=(
            "Whether graph state is persisted beyond the current invocation."
        ),
    )
    checkpoint_backend: Literal["none"] = "none"
    conversation_memory_backend: Literal["in_process_session_store"] = Field(
        default="in_process_session_store",
        description=(
            "Conversation memory is stored separately from per-run graph state."
        ),
    )
    execution_trace: list[str] = Field(
        default_factory=list,
        description="Nodes completed during this workflow run, in execution order.",
    )
    retrieval_attempts: dict[str, int] = Field(
        default_factory=dict,
        description="Research-node attempts by specialist agent.",
    )
    retrieval_statuses: dict[
        str,
        Literal["pending", "retrying", "succeeded", "exhausted"],
    ] = Field(
        default_factory=dict,
        description="Final research status for each specialist agent.",
    )
    document_retrieval_stats: dict[str, int] = Field(
        default_factory=dict,
        description="Uploaded documents, pages, and chunks processed for embeddings.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal workflow limitations or fallback events.",
    )


class WorkflowGraphNode(BaseModel):
    name: str
    kind: Literal["control", "agent", "research", "deterministic"]
    description: str


class WorkflowGraphEdge(BaseModel):
    source: str
    target: str
    condition: str | None = None


class WorkflowGraphManifest(BaseModel):
    name: str = "bastion_diligence_graph"
    state_model: str = "BastionGraphState"
    state_scope: Literal["single_run"] = "single_run"
    checkpointing_enabled: bool = False
    checkpoint_backend: Literal["none"] = "none"
    conversation_memory_backend: Literal["in_process_session_store"] = (
        "in_process_session_store"
    )
    nodes: list[WorkflowGraphNode]
    edges: list[WorkflowGraphEdge]


class AnalyzeResponse(BaseModel):
    session_id: str
    orchestration_plan: OrchestrationPlan
    market_analysis: MarketAnalysis
    financial_analysis: FinancialAnalysis
    risk_analysis: RiskAnalysis
    investment_memo: InvestmentMemo
    report: ReportPackage
    workflow_diagnostics: WorkflowDiagnostics


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
