import json
import logging
import operator
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from checkpointing import get_postgres_checkpointer
from agents.financial_agent import run_financial_agent
from agents.market_agent import run_market_agent
from agents.memo_agent import run_memo_agent
from agents.orchestrator_agent import DEFAULT_PLAN, run_orchestrator_agent
from agents.risk_agent import run_risk_agent
from document_retrieval import build_agent_document_contexts
from memory import memory_store
from report_service import build_report_package
from schemas import (
    AgentExecutionStep,
    AnalyzeRequest,
    AnalyzeResponse,
    FinancialAnalysis,
    InvestmentMemo,
    MarketAnalysis,
    OrchestrationPlan,
    ReportPackage,
    RiskAnalysis,
    WorkflowDiagnostics,
    WorkflowGraphEdge,
    WorkflowGraphManifest,
    WorkflowGraphNode,
)
from tools.financial_research import build_financial_research_context
from tools.market_research import build_market_research_context
from tools.risk_research import build_risk_research_context

SpecialistRunner = Callable[[str, str | None], object]
ResearchBuilder = Callable[[str], object]
ResearchStatus = Literal["pending", "retrying", "succeeded", "exhausted"]

DEFAULT_RETRIEVAL_ATTEMPTS = 3
GRAPH_RECURSION_LIMIT = 32

logger = logging.getLogger("bastion.workflow")


class BastionGraphState(TypedDict, total=False):
    workflow_run_id: str
    session_id: str
    company_text: str
    document_source_text: str
    orchestration_plan: OrchestrationPlan
    market_analysis: MarketAnalysis
    financial_analysis: FinancialAnalysis
    risk_analysis: RiskAnalysis
    investment_memo: InvestmentMemo
    report: ReportPackage
    research_contexts: dict[str, str]
    document_contexts: dict[str, str]
    document_retrieval_stats: dict[str, int]
    retrieval_attempts: dict[str, int]
    retrieval_statuses: dict[str, ResearchStatus]
    retrieval_errors: dict[str, str]
    max_retrieval_attempts: int
    execution_trace: Annotated[list[str], operator.add]
    workflow_warnings: Annotated[list[str], operator.add]


SPECIALIST_RUNNERS: dict[str, SpecialistRunner] = {
    "market_agent": run_market_agent,
    "financial_agent": run_financial_agent,
    "risk_agent": run_risk_agent,
}

RESEARCH_BUILDERS: dict[str, ResearchBuilder] = {
    "market_agent": build_market_research_context,
    "financial_agent": build_financial_research_context,
    "risk_agent": build_risk_research_context,
}

SYNTHESIS_RUNNERS = {
    "memo_agent": run_memo_agent,
}

SPECIALIST_OUTPUT_KEYS = {
    "market_agent": "market_analysis",
    "financial_agent": "financial_analysis",
    "risk_agent": "risk_analysis",
}

WORKFLOW_GRAPH_MANIFEST = WorkflowGraphManifest(
    nodes=[
        WorkflowGraphNode(
            name="START",
            kind="control",
            description="Receives the initial request-scoped graph state.",
        ),
        WorkflowGraphNode(
            name="orchestrator_agent",
            kind="agent",
            description="Builds the ordered diligence plan and tool assignments.",
        ),
        WorkflowGraphNode(
            name="document_retrieval",
            kind="research",
            description="Embeds uploaded S3 PDFs and selects agent-specific excerpts.",
        ),
        WorkflowGraphNode(
            name="market_research",
            kind="research",
            description="Collects live market context and retries transient failures.",
        ),
        WorkflowGraphNode(
            name="market_agent",
            kind="agent",
            description="Writes the market analysis into shared graph state.",
        ),
        WorkflowGraphNode(
            name="financial_research",
            kind="research",
            description="Extracts financial evidence and public-market context.",
        ),
        WorkflowGraphNode(
            name="financial_agent",
            kind="agent",
            description="Uses market output to write the financial analysis.",
        ),
        WorkflowGraphNode(
            name="risk_research",
            kind="research",
            description="Collects internal and current external risk signals.",
        ),
        WorkflowGraphNode(
            name="risk_agent",
            kind="agent",
            description="Uses market and financial outputs to write risk analysis.",
        ),
        WorkflowGraphNode(
            name="memo_agent",
            kind="agent",
            description="Synthesizes every specialist output into the IC memo.",
        ),
        WorkflowGraphNode(
            name="build_report",
            kind="deterministic",
            description="Builds the final structured report without an LLM call.",
        ),
        WorkflowGraphNode(
            name="END",
            kind="control",
            description="Marks successful completion of the workflow run.",
        ),
    ],
    edges=[
        WorkflowGraphEdge(source="START", target="orchestrator_agent"),
        WorkflowGraphEdge(source="orchestrator_agent", target="document_retrieval"),
        WorkflowGraphEdge(source="document_retrieval", target="market_research"),
        WorkflowGraphEdge(
            source="market_research",
            target="market_research",
            condition="retry while retrieval_status is retrying",
        ),
        WorkflowGraphEdge(
            source="market_research",
            target="market_agent",
            condition="continue after success or retry exhaustion",
        ),
        WorkflowGraphEdge(source="market_agent", target="financial_research"),
        WorkflowGraphEdge(
            source="financial_research",
            target="financial_research",
            condition="retry while retrieval_status is retrying",
        ),
        WorkflowGraphEdge(
            source="financial_research",
            target="financial_agent",
            condition="continue after success or retry exhaustion",
        ),
        WorkflowGraphEdge(source="financial_agent", target="risk_research"),
        WorkflowGraphEdge(
            source="risk_research",
            target="risk_research",
            condition="retry while retrieval_status is retrying",
        ),
        WorkflowGraphEdge(
            source="risk_research",
            target="risk_agent",
            condition="continue after success or retry exhaustion",
        ),
        WorkflowGraphEdge(source="risk_agent", target="memo_agent"),
        WorkflowGraphEdge(source="memo_agent", target="build_report"),
        WorkflowGraphEdge(source="build_report", target="END"),
    ],
)


def _format_analyze_request_context(request: AnalyzeRequest) -> str:
    if any(
        [
            request.buyer_context,
            request.target_context,
            request.deal_context,
            request.questions,
        ]
    ):
        questions = "\n".join(
            f"{index}. {question.strip()}"
            for index, question in enumerate(request.questions, start=1)
            if question.strip()
        )
        legacy_context = request.company_text.strip() if request.company_text else ""
        return f"""
Buyer / acquirer context:
{request.buyer_context or "Not provided."}

Target company:
{request.target_context or "Not provided."}

Deal thesis / transaction context:
{request.deal_context or legacy_context or "Not provided."}

Explicit user questions:
{questions or "Use the buyer, target, and deal context to produce the core M&A comparison."}
"""

    return request.company_text or ""


def _stringify_output(output: object, max_chars: int = 10000) -> str:
    if hasattr(output, "model_dump_json"):
        text = output.model_dump_json(indent=2)
    else:
        text = str(output)
    if len(text) > max_chars:
        return f"{text[:max_chars].rstrip()}... [truncated]"
    return text


def _step_for_agent(plan: OrchestrationPlan, agent_name: str) -> AgentExecutionStep:
    for step in plan.steps:
        if step.agent_name == agent_name:
            return step
    if plan is not DEFAULT_PLAN:
        for step in DEFAULT_PLAN.steps:
            if step.agent_name == agent_name:
                return step
    raise ValueError(f"No orchestration step exists for {agent_name}.")


def _agent_context(
    company_text: str,
    step: AgentExecutionStep,
    prior_outputs: dict[str, object],
) -> str:
    prior_context = "\n\n".join(
        f"{agent} output:\n{_stringify_output(output)}"
        for agent, output in prior_outputs.items()
    )
    prior_block = (
        f"\nCompleted prior agent outputs:\n{prior_context}"
        if prior_context
        else ""
    )
    return f"""
Company context:
{company_text}

CFO orchestration instruction:
{step.model_dump_json(indent=2)}
{prior_block}
"""


def _workflow_memory_summary(memo: InvestmentMemo, report: ReportPackage) -> str:
    limitations = "; ".join(report.source_limitations[:3]) or "None noted"
    open_questions = "; ".join(memo.open_questions[:3]) or "None"
    return (
        f"Recommendation: {memo.recommendation}. "
        f"Summary: {memo.executive_summary} "
        f"Confidence: {memo.overall_confidence}. "
        f"Source limitations: {limitations}. "
        f"Open questions: {open_questions}."
    )


def _run_orchestrator_node(state: BastionGraphState) -> dict[str, object]:
    logger.info("Starting orchestrator agent")
    try:
        plan = run_orchestrator_agent(state["company_text"])
        warnings: list[str] = []
    except Exception as error:
        logger.exception("Orchestrator failed; using default plan")
        plan = DEFAULT_PLAN
        warnings = [
            "The orchestrator failed and Bastion used its validated default plan: "
            f"{type(error).__name__}."
        ]
    logger.info("Finished orchestrator agent")
    return {
        "orchestration_plan": plan,
        "execution_trace": ["orchestrator_agent"],
        "workflow_warnings": warnings,
    }


def _run_document_retrieval_node(state: BastionGraphState) -> dict[str, object]:
    logger.info("Starting uploaded-document embedding retrieval")
    try:
        contexts, stats = build_agent_document_contexts(
            state.get("document_source_text", state["company_text"]),
            state["orchestration_plan"],
        )
        warnings: list[str] = []
    except Exception as error:
        logger.exception("Uploaded-document embedding retrieval failed")
        contexts = {}
        stats = {"documents": 0, "pages": 0, "chunks": 0}
        warnings = [
            "Uploaded-document embedding retrieval was unavailable; specialists "
            f"continued with supplied text and external research: {type(error).__name__}."
        ]
    logger.info("Finished uploaded-document embedding retrieval: %s", stats)
    return {
        "document_contexts": contexts,
        "document_retrieval_stats": stats,
        "execution_trace": ["document_retrieval"],
        "workflow_warnings": warnings,
    }


def _serialize_research_context(research_context: object) -> str:
    if hasattr(research_context, "to_prompt_json"):
        return research_context.to_prompt_json()
    if hasattr(research_context, "model_dump_json"):
        return research_context.model_dump_json(indent=2)
    if isinstance(research_context, str):
        return research_context
    return json.dumps(research_context, default=str, indent=2)


def _retrieval_failure_detail(research_context: object) -> str | None:
    if getattr(research_context, "retrieval_succeeded", True):
        return None
    errors = getattr(research_context, "retrieval_errors", [])
    if errors:
        return "; ".join(str(error) for error in errors)[:2000]
    return "The research provider returned no successful retrieval attempts."


def _research_error_packet(
    agent_name: str,
    attempt: int,
    detail: str,
) -> str:
    return json.dumps(
        {
            "retrieval_succeeded": False,
            "agent_name": agent_name,
            "attempts": attempt,
            "error": detail,
            "instruction": (
                "Treat external research as unavailable. Use only supplied deal "
                "context, label unsupported points, and preserve this limitation."
            ),
        },
        indent=2,
    )


def _run_research_node(
    state: BastionGraphState,
    agent_name: str,
) -> dict[str, object]:
    attempts = dict(state.get("retrieval_attempts", {}))
    statuses = dict(state.get("retrieval_statuses", {}))
    errors = dict(state.get("retrieval_errors", {}))
    contexts = dict(state.get("research_contexts", {}))

    attempt = attempts.get(agent_name, 0) + 1
    attempts[agent_name] = attempt
    max_attempts = max(1, state.get(
        "max_retrieval_attempts",
        DEFAULT_RETRIEVAL_ATTEMPTS,
    ))
    node_name = f"{agent_name.removesuffix('_agent')}_research"

    try:
        research_context = RESEARCH_BUILDERS[agent_name](state["company_text"])
        serialized_context = _serialize_research_context(research_context)
        failure_detail = _retrieval_failure_detail(research_context)
    except Exception as error:
        logger.exception(
            "Research node failed for %s on attempt %s",
            agent_name,
            attempt,
        )
        failure_detail = f"{type(error).__name__}: {error}"[:2000]
        serialized_context = _research_error_packet(
            agent_name,
            attempt,
            failure_detail,
        )

    update: dict[str, object] = {
        "retrieval_attempts": attempts,
        "retrieval_statuses": statuses,
        "retrieval_errors": errors,
        "research_contexts": contexts,
        "execution_trace": [f"{node_name}:{attempt}"],
    }

    if failure_detail is None:
        statuses[agent_name] = "succeeded"
        errors.pop(agent_name, None)
        contexts[agent_name] = serialized_context
        logger.info(
            "Research succeeded for %s on attempt %s",
            agent_name,
            attempt,
        )
        return update

    errors[agent_name] = failure_detail
    contexts[agent_name] = serialized_context
    if attempt < max_attempts:
        statuses[agent_name] = "retrying"
        logger.warning(
            "Research failed for %s on attempt %s/%s; retrying",
            agent_name,
            attempt,
            max_attempts,
        )
        return update

    statuses[agent_name] = "exhausted"
    contexts[agent_name] = _research_error_packet(
        agent_name,
        attempt,
        failure_detail,
    )
    update["workflow_warnings"] = [
        f"{agent_name} research failed after {attempt} attempts. "
        "The specialist continued with supplied deal context and an explicit "
        "research limitation."
    ]
    logger.error(
        "Research exhausted for %s after %s attempts",
        agent_name,
        attempt,
    )
    return update


def _run_market_research_node(state: BastionGraphState) -> dict[str, object]:
    return _run_research_node(state, "market_agent")


def _run_financial_research_node(state: BastionGraphState) -> dict[str, object]:
    return _run_research_node(state, "financial_agent")


def _run_risk_research_node(state: BastionGraphState) -> dict[str, object]:
    return _run_research_node(state, "risk_agent")


def _route_research(
    state: BastionGraphState,
    agent_name: str,
) -> Literal["retry", "continue"]:
    if state.get("retrieval_statuses", {}).get(agent_name) == "retrying":
        return "retry"
    return "continue"


def _route_market_research(
    state: BastionGraphState,
) -> Literal["retry", "continue"]:
    return _route_research(state, "market_agent")


def _route_financial_research(
    state: BastionGraphState,
) -> Literal["retry", "continue"]:
    return _route_research(state, "financial_agent")


def _route_risk_research(
    state: BastionGraphState,
) -> Literal["retry", "continue"]:
    return _route_research(state, "risk_agent")


def _prior_outputs_for_agent(
    state: BastionGraphState,
    agent_name: str,
) -> dict[str, object]:
    if agent_name == "financial_agent":
        return {"market_agent": state["market_analysis"]}
    if agent_name == "risk_agent":
        return {
            "market_agent": state["market_analysis"],
            "financial_agent": state["financial_analysis"],
        }
    return {}


def _run_specialist_node(
    state: BastionGraphState,
    agent_name: str,
) -> dict[str, object]:
    plan = state["orchestration_plan"]
    step = _step_for_agent(plan, agent_name)
    context = _agent_context(
        state["company_text"],
        step,
        _prior_outputs_for_agent(state, agent_name),
    )
    research_context = state.get("research_contexts", {}).get(agent_name)
    document_context = state.get("document_contexts", {}).get(agent_name)
    if document_context:
        research_context = (
            "Uploaded-document excerpts selected by embedding retrieval:\n"
            f"{document_context}\n\nExternal and deterministic research:\n"
            f"{research_context or 'No additional research context available.'}"
        )

    logger.info("Starting specialist agent: %s", agent_name)
    output = SPECIALIST_RUNNERS[agent_name](context, research_context)
    logger.info("Finished specialist agent: %s", agent_name)

    return {
        SPECIALIST_OUTPUT_KEYS[agent_name]: output,
        "execution_trace": [agent_name],
    }


def _run_market_node(state: BastionGraphState) -> dict[str, object]:
    return _run_specialist_node(state, "market_agent")


def _run_financial_node(state: BastionGraphState) -> dict[str, object]:
    return _run_specialist_node(state, "financial_agent")


def _run_risk_node(state: BastionGraphState) -> dict[str, object]:
    return _run_specialist_node(state, "risk_agent")


def _run_memo_node(state: BastionGraphState) -> dict[str, object]:
    memo_step = _step_for_agent(state["orchestration_plan"], "memo_agent")
    logger.info("Starting memo agent")
    memo = SYNTHESIS_RUNNERS["memo_agent"](
        company_text=_agent_context(
            state["company_text"],
            memo_step,
            {},
        ),
        market_analysis=state["market_analysis"],
        financial_analysis=state["financial_analysis"],
        risk_analysis=state["risk_analysis"],
    )
    logger.info("Finished memo agent")
    return {
        "investment_memo": memo,
        "execution_trace": ["memo_agent"],
    }


def _build_report_node(state: BastionGraphState) -> dict[str, object]:
    logger.info("Building report package")
    report = build_report_package(
        state["orchestration_plan"],
        state["market_analysis"],
        state["financial_analysis"],
        state["risk_analysis"],
        state["investment_memo"],
    )
    return {
        "report": report,
        "execution_trace": ["build_report"],
    }


def get_diligence_graph_manifest() -> WorkflowGraphManifest:
    return WORKFLOW_GRAPH_MANIFEST.model_copy(deep=True)


def _build_workflow_diagnostics(
    state: BastionGraphState,
) -> WorkflowDiagnostics:
    return WorkflowDiagnostics(
        workflow_run_id=state["workflow_run_id"],
        execution_trace=list(state.get("execution_trace", [])),
        retrieval_attempts=dict(state.get("retrieval_attempts", {})),
        retrieval_statuses=dict(state.get("retrieval_statuses", {})),
        document_retrieval_stats=dict(
            state.get("document_retrieval_stats", {})
        ),
        warnings=list(state.get("workflow_warnings", [])),
    )


def build_diligence_graph(checkpointer=None):
    graph = StateGraph(BastionGraphState)
    graph.add_node("orchestrator_agent", _run_orchestrator_node)
    graph.add_node("document_retrieval", _run_document_retrieval_node)
    graph.add_node("market_research", _run_market_research_node)
    graph.add_node("market_agent", _run_market_node)
    graph.add_node("financial_research", _run_financial_research_node)
    graph.add_node("financial_agent", _run_financial_node)
    graph.add_node("risk_research", _run_risk_research_node)
    graph.add_node("risk_agent", _run_risk_node)
    graph.add_node("memo_agent", _run_memo_node)
    graph.add_node("build_report", _build_report_node)

    graph.add_edge(START, "orchestrator_agent")
    graph.add_edge("orchestrator_agent", "document_retrieval")
    graph.add_edge("document_retrieval", "market_research")
    graph.add_conditional_edges(
        "market_research",
        _route_market_research,
        {
            "retry": "market_research",
            "continue": "market_agent",
        },
    )
    graph.add_edge("market_agent", "financial_research")
    graph.add_conditional_edges(
        "financial_research",
        _route_financial_research,
        {
            "retry": "financial_research",
            "continue": "financial_agent",
        },
    )
    graph.add_edge("financial_agent", "risk_research")
    graph.add_conditional_edges(
        "risk_research",
        _route_risk_research,
        {
            "retry": "risk_research",
            "continue": "risk_agent",
        },
    )
    graph.add_edge("risk_agent", "memo_agent")
    graph.add_edge("memo_agent", "build_report")
    graph.add_edge("build_report", END)
    return graph.compile(checkpointer=checkpointer)


@lru_cache(maxsize=1)
def get_durable_diligence_graph():
    return build_diligence_graph(checkpointer=get_postgres_checkpointer())


def run_investment_banking_workflow(request: AnalyzeRequest) -> AnalyzeResponse:
    workflow_run_id = str(uuid4())
    session = memory_store.get_or_create(request.session_id)
    memory_context = memory_store.get_recent_context(session.session_id)
    deal_context = _format_analyze_request_context(request)
    company_text_with_memory = f"""
Conversation memory for this session:
{memory_context}

Current structured M&A deal context:
{deal_context}
"""

    memory_store.add_message(session.session_id, "user", deal_context)

    initial_state: BastionGraphState = {
        "workflow_run_id": workflow_run_id,
        "session_id": session.session_id,
        "company_text": company_text_with_memory,
        "document_source_text": deal_context,
        "research_contexts": {},
        "document_contexts": {},
        "document_retrieval_stats": {},
        "retrieval_attempts": {},
        "retrieval_statuses": {},
        "retrieval_errors": {},
        "max_retrieval_attempts": DEFAULT_RETRIEVAL_ATTEMPTS,
        "execution_trace": [],
        "workflow_warnings": [],
    }
    final_state = get_durable_diligence_graph().invoke(
        initial_state,
        config={
            "recursion_limit": GRAPH_RECURSION_LIMIT,
            "configurable": {
                "thread_id": workflow_run_id,
                "checkpoint_ns": "diligence",
            },
        },
    )

    investment_memo = final_state["investment_memo"]
    report = final_state["report"]
    memory_store.add_message(
        session.session_id,
        "assistant",
        _workflow_memory_summary(investment_memo, report),
    )

    return AnalyzeResponse(
        session_id=session.session_id,
        orchestration_plan=final_state["orchestration_plan"],
        market_analysis=final_state["market_analysis"],
        financial_analysis=final_state["financial_analysis"],
        risk_analysis=final_state["risk_analysis"],
        investment_memo=investment_memo,
        report=report,
        workflow_diagnostics=_build_workflow_diagnostics(final_state),
    )
