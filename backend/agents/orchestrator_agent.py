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
                    tool_name="document_search",
                    purpose="Find source-backed risk evidence in provided context.",
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
