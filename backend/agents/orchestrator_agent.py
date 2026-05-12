from backend.gemini_client import call_gemini_structured
from backend.schemas import AgentExecutionStep, OrchestrationPlan, ToolAssignment


DEFAULT_PLAN = OrchestrationPlan(
    cfo_rationale=(
        "Run a bank-style M&A diligence sequence: establish market context, "
        "translate that context into financial and valuation implications, "
        "then assess acquisition risk and synthesize the investment committee memo."
    ),
    steps=[
        AgentExecutionStep(
            agent_name="market_agent",
            execution_group=1,
            objective=(
                "Establish market backdrop, sector structure, buyer appetite, "
                "valuation sentiment, demand, competition, and deal timing implications."
            ),
            tools=[
                ToolAssignment(
                    tool_name="market_research",
                    purpose="Identify industry and competitive context from available sources.",
                ),
                ToolAssignment(
                    tool_name="live_market_data",
                    purpose=(
                        "Pull public-company and market proxy price moves that "
                        "affect valuation, financing, and buyer appetite."
                    ),
                ),
                ToolAssignment(
                    tool_name="deal_market_news_search",
                    purpose=(
                        "Search current deal, sector, regulatory, demand, and "
                        "competitive news relevant to the M&A process."
                    ),
                ),
                ToolAssignment(
                    tool_name="public_market_proxy_analysis",
                    purpose=(
                        "Use sector ETFs, equity indices, and credit proxies as "
                        "transaction-market indicators when the target is private."
                    ),
                ),
                ToolAssignment(
                    tool_name="document_search",
                    purpose="Find market-related evidence in provided company context.",
                ),
            ],
        ),
        AgentExecutionStep(
            agent_name="financial_agent",
            execution_group=2,
            objective=(
                "Build financial, QoE, liquidity, valuation, and deal-structure "
                "analysis using company data plus market-agent read-through."
            ),
            context_needed=["market_agent"],
            tools=[
                ToolAssignment(
                    tool_name="financial_metric_extraction",
                    purpose="Extract relevant annual-report-style financial metrics.",
                ),
                ToolAssignment(
                    tool_name="growth_rate_calculator",
                    purpose="Calculate growth rates when prior-period values are available.",
                ),
                ToolAssignment(
                    tool_name="margin_calculator",
                    purpose="Calculate margin profile when revenue and profit metrics exist.",
                ),
                ToolAssignment(
                    tool_name="valuation_multiple_calculator",
                    purpose="Assess valuation support when EV, revenue, or EBITDA is available.",
                ),
                ToolAssignment(
                    tool_name="quality_of_earnings_review",
                    purpose=(
                        "Identify revenue quality, normalized earnings, one-time "
                        "items, margin durability, and source limitations."
                    ),
                ),
                ToolAssignment(
                    tool_name="working_capital_analysis",
                    purpose=(
                        "Flag working-capital seasonality, cash conversion, and "
                        "purchase price adjustment diligence needs."
                    ),
                ),
                ToolAssignment(
                    tool_name="purchase_price_adjustment_analysis",
                    purpose=(
                        "Identify cash, debt, net working capital, debt-like item, "
                        "and earnout/escrow implications."
                    ),
                ),
                ToolAssignment(
                    tool_name="debt_capacity_screen",
                    purpose=(
                        "Assess financing risk and leverage capacity from cash "
                        "flow, margins, growth, and market conditions."
                    ),
                ),
                ToolAssignment(
                    tool_name="live_market_data",
                    purpose=(
                        "Pull explicit public comparable or company ticker data "
                        "to frame current valuation and trading-context signals."
                    ),
                ),
            ],
        ),
        AgentExecutionStep(
            agent_name="risk_agent",
            execution_group=3,
            objective=(
                "Create acquisition risk matrix, diligence workplan, closing-risk "
                "view, integration-risk view, and purchase agreement implications."
            ),
            context_needed=["market_agent", "financial_agent"],
            tools=[
                ToolAssignment(
                    tool_name="risk_register",
                    purpose="Prioritize risks by severity and deal impact.",
                ),
                ToolAssignment(
                    tool_name="acquisition_risk_matrix",
                    purpose=(
                        "Map commercial, legal, regulatory, cyber, integration, "
                        "financial, and transaction-process risks to M&A impact."
                    ),
                ),
                ToolAssignment(
                    tool_name="document_search",
                    purpose="Find source-backed risk evidence in provided context.",
                ),
                ToolAssignment(
                    tool_name="deal_market_news_search",
                    purpose=(
                        "Search current legal, regulatory, cybersecurity, and "
                        "sector-risk signals that could affect the M&A process."
                    ),
                ),
                ToolAssignment(
                    tool_name="regulatory_risk_search",
                    purpose=(
                        "Check antitrust, sector approval, privacy, and foreign "
                        "investment risks relevant to closing certainty."
                    ),
                ),
                ToolAssignment(
                    tool_name="cyber_diligence_screen",
                    purpose=(
                        "Screen cyber, data privacy, and sensitive-data risks that "
                        "could affect diligence, indemnity, or integration."
                    ),
                ),
                ToolAssignment(
                    tool_name="integration_risk_assessment",
                    purpose=(
                        "Assess post-close integration, synergy, customer retention, "
                        "and operating-continuity risks."
                    ),
                ),
                ToolAssignment(
                    tool_name="purchase_agreement_risk_mapper",
                    purpose=(
                        "Translate material risks into reps, warranties, covenants, "
                        "escrow, indemnity, earnout, and closing-condition implications."
                    ),
                ),
            ],
        ),
        AgentExecutionStep(
            agent_name="memo_agent",
            execution_group=4,
            objective=(
                "Synthesize market, financial, and risk outputs into a disciplined "
                "investment committee memo with recommendation, conditions, and source limits."
            ),
            context_needed=["market_agent", "financial_agent", "risk_agent"],
            tools=[
                ToolAssignment(
                    tool_name="memo_synthesis",
                    purpose="Combine specialist outputs into a decision-focused report.",
                ),
                ToolAssignment(
                    tool_name="citation_builder",
                    purpose="Preserve source-backed claims from specialist outputs.",
                ),
                ToolAssignment(
                    tool_name="investment_committee_memo_builder",
                    purpose=(
                        "Convert specialist analysis into IC-ready recommendation, "
                        "conditions, diligence gates, and decision logic."
                    ),
                ),
                ToolAssignment(
                    tool_name="evidence_reconciliation",
                    purpose=(
                        "Resolve conflicts across market, financial, and risk "
                        "outputs and expose unsupported assumptions."
                    ),
                ),
            ],
        ),
    ],
)


def run_orchestrator_agent(company_text: str) -> OrchestrationPlan:
    return call_gemini_structured(
        f"""
You are Bastion's CFO Orchestrator Agent. You manage the market, financial,
risk, and memo agents for an AI-powered investment banking diligence workflow.

Create a logical M&A diligence execution plan similar to publicly observable,
top-tier investment banking workflows. Do not claim proprietary bank access or
private internal methodology.

Keep the plan efficient. Do not add unnecessary steps. Do not invent agents or
tools. Use the execution_group field only to express sequence. Assign distinct
groups to market_agent, financial_agent, risk_agent, and memo_agent so the core
diligence process remains sequential.

Use this sequence:
1. market_agent: market, buyer universe, valuation sentiment, and sector context
2. financial_agent: financial quality, valuation, liquidity, and deal-structure implications
3. risk_agent: acquisition risk, diligence workplan, closing risk, and purchase agreement implications
4. memo_agent: investment committee synthesis and recommendation

Market analysis must inform financial assumptions. Financial analysis must
inform risk, purchase price adjustment, and deal-term analysis. All specialist
outputs must inform memo synthesis.

Every step should specify the upstream context it depends on and assign only
tools that materially improve the answer.

Planning standard:
- identify the target, buyer, sector, geography, transaction type, and missing inputs when available
- force agents to distinguish source-backed facts, live-tool evidence, analyst inference, user assumptions, and unknowns
- require deal-specific output tied to valuation, buyer appetite, financing, diligence scope, closing certainty, or purchase agreement terms
- do not allow unsupported market facts, metrics, valuation multiples, risks, dates, or citations to pass through as facts
- surface missing information as diligence requests instead of asking agents to guess

Company context:
{company_text}
""",
        OrchestrationPlan,
    )
