from backend.gemini_client import call_gemini_structured
from backend.schemas import AgentExecutionStep, OrchestrationPlan, ToolAssignment


DEFAULT_PLAN = OrchestrationPlan(
    cfo_rationale=(
        "Run independent diligence specialists in parallel to reduce latency, "
        "then run memo synthesis sequentially after specialist outputs exist."
    ),
    steps=[
        AgentExecutionStep(
            agent_name="market_agent",
            execution_group=1,
            objective="Assess market position, demand drivers, competition, and growth risks.",
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
            execution_group=1,
            objective="Build financial analysis and investment thesis contribution.",
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
            execution_group=1,
            objective="Identify financial, operating, market, legal, and execution risks.",
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
            execution_group=2,
            objective="Synthesize specialist outputs into the final investment memo.",
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
            ],
        ),
    ],
)


def run_orchestrator_agent(company_text: str) -> OrchestrationPlan:
    return call_gemini_structured(
        f"""
You are Bastion's CFO Orchestrator Agent. You manage the market, financial,
risk, and memo agents for an AI-powered investment banking diligence workflow.

Create a logical execution plan. Decide which agents can run in parallel and
which must run sequentially. Assign only the available tools listed in the JSON
schema. Market, financial, and risk work usually run in parallel unless one
clearly depends on another. Memo synthesis must run after the relevant
specialist outputs exist.

Keep the plan efficient. Do not add unnecessary steps. Do not invent agents or
tools. The execution_group field controls order: same group runs in parallel;
higher groups wait for lower groups.

Company context:
{company_text}
""",
        OrchestrationPlan,
    )
