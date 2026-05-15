from backend.schemas import (
    AgentContribution,
    AgentName,
    FinancialAnalysis,
    FinancialCitation,
    InvestmentMemo,
    MarketAnalysis,
    OrchestrationPlan,
    ReportCitation,
    ReportPackage,
    ReportSection,
    RiskAnalysis,
)


AGENT_LABELS: dict[AgentName, str] = {
    "market_agent": "Market Agent",
    "financial_agent": "Financial Agent",
    "risk_agent": "Risk Agent",
    "memo_agent": "Memo Agent",
}


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _clean_list(values: list[object], limit: int = 6) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def _agent_output_citation(agent_name: AgentName, relevance: str) -> ReportCitation:
    return ReportCitation(
        agent_name=agent_name,
        source_type="agent_output",
        title=f"{AGENT_LABELS[agent_name]} structured output",
        source=f"{agent_name} output",
        relevance=relevance,
    )


def _infer_financial_source_type(citation: FinancialCitation) -> str:
    source = citation.source.lower()
    if citation.page is not None:
        return "document"
    if "calculated" in source or "formula" in source:
        return "calculated_metric"
    if "inference" in source:
        return "analyst_inference"
    return "company_context"


def _financial_citation(
    agent_name: AgentName,
    citation: FinancialCitation | None,
    title: str,
    relevance: str,
) -> ReportCitation | None:
    if citation is None:
        return None

    return ReportCitation(
        agent_name=agent_name,
        source_type=_infer_financial_source_type(citation),
        title=title or citation.source,
        source=citation.source,
        relevance=relevance,
        page=citation.page,
        excerpt=citation.excerpt,
    )


def _dedupe_citations(citations: list[ReportCitation], limit: int | None = None) -> list[ReportCitation]:
    deduped: list[ReportCitation] = []
    seen: set[tuple[object, ...]] = set()
    for citation in citations:
        key = (
            citation.agent_name,
            citation.source_type,
            citation.title,
            citation.source,
            citation.url,
            citation.page,
            citation.excerpt,
        )
        if key in seen:
            continue
        deduped.append(citation)
        seen.add(key)
        if limit is not None and len(deduped) >= limit:
            break
    return deduped


def _market_citations(market: MarketAnalysis) -> list[ReportCitation]:
    citations = [
        _agent_output_citation(
            "market_agent",
            "Specialist market output used for final thesis, market timing, and sector read-through.",
        )
    ]
    for source in market.research_sources:
        citations.append(
            ReportCitation(
                agent_name="market_agent",
                source_type=source.source_type,
                title=source.title,
                source=source.publisher or source.title,
                publisher=source.publisher,
                url=source.url,
                relevance=source.relevance,
                as_of=source.as_of,
            )
        )
    return _dedupe_citations(citations, limit=10)


def _financial_citations(financial: FinancialAnalysis) -> list[ReportCitation]:
    citations = [
        _agent_output_citation(
            "financial_agent",
            "Specialist financial output used for valuation support, quality of earnings, and financing view.",
        )
    ]

    for metric in financial.key_metrics:
        citation = _financial_citation(
            "financial_agent",
            metric.citation,
            metric.name,
            metric.interpretation,
        )
        if citation:
            citations.append(citation)

    for finding in [
        *financial.financial_strengths,
        *financial.financial_concerns,
        *financial.red_flags,
    ]:
        citation = _financial_citation(
            "financial_agent",
            finding.citation,
            finding.title,
            finding.detail,
        )
        if citation:
            citations.append(citation)

    return _dedupe_citations(citations, limit=12)


def _risk_citations(risk: RiskAnalysis) -> list[ReportCitation]:
    citations = [
        _agent_output_citation(
            "risk_agent",
            "Specialist risk output used for diligence gates, purchase agreement protections, and proceed/pause logic.",
        )
    ]

    for source in risk.risk_sources:
        citations.append(
            ReportCitation(
                agent_name="risk_agent",
                source_type=source.source_type,
                title=source.title,
                source=source.publisher or source.title,
                publisher=source.publisher,
                url=source.url,
                relevance=source.relevance,
                as_of=source.as_of,
            )
        )

    for item in [*risk.top_risks, *risk.red_flags, *risk.deal_breaker_risks]:
        citation = _financial_citation(
            "risk_agent",
            item.citation,
            item.title,
            item.deal_impact,
        )
        if citation:
            citations.append(citation)

    for factor in risk.acquisition_risk_factors:
        citation = _financial_citation(
            "risk_agent",
            factor.citation,
            factor.finding,
            factor.source_signal,
        )
        if citation:
            citations.append(citation)
        elif factor.source_signal:
            citations.append(
                ReportCitation(
                    agent_name="risk_agent",
                    source_type=(
                        "analyst_inference"
                        if factor.diligence_status == "analyst_inference"
                        else "company_context"
                    ),
                    title=factor.finding,
                    source=factor.diligence_status,
                    relevance=factor.source_signal,
                )
            )

    return _dedupe_citations(citations, limit=12)


def _memo_citations(memo: InvestmentMemo) -> list[ReportCitation]:
    citations = [
        _agent_output_citation(
            "memo_agent",
            "Final synthesis output used for recommendation, conditions, and open questions.",
        )
    ]

    for point in memo.key_data_points:
        citation = _financial_citation(
            point.source_agent,
            point.citation,
            point.label,
            point.value,
        )
        if citation:
            citations.append(citation)
        else:
            citations.append(
                ReportCitation(
                    agent_name=point.source_agent,
                    source_type="agent_output",
                    title=point.label,
                    source=f"{point.source_agent} output",
                    relevance=point.value,
                )
            )

    return _dedupe_citations(citations, limit=10)


def _market_contribution(market: MarketAnalysis) -> AgentContribution:
    key_findings = _clean_list(
        [
            market.headline,
            market.market_position,
            market.market_backdrop,
            *[finding.title for finding in market.growth_drivers],
            *[finding.title for finding in market.competitive_risks],
            *[factor.factor for factor in market.key_market_factors],
        ],
        limit=7,
    )
    provides = _clean_list(
        [
            market.investment_thesis_contribution,
            market.m_and_a_implications,
            market.capital_markets_read_through,
            market.pricing_and_margin_pressure,
        ],
        limit=5,
    )
    return AgentContribution(
        agent_name="market_agent",
        label=AGENT_LABELS["market_agent"],
        summary=market.executive_summary,
        provides_to_final_solution=provides,
        key_findings=key_findings,
        citations=_market_citations(market),
        confidence=market.overall_confidence,
    )


def _financial_contribution(financial: FinancialAnalysis) -> AgentContribution:
    key_findings = _clean_list(
        [
            financial.headline,
            financial.revenue_quality,
            financial.quality_of_earnings_view,
            financial.valuation_view,
            *[finding.title for finding in financial.financial_strengths],
            *[finding.title for finding in financial.financial_concerns],
            *[finding.title for finding in financial.red_flags],
        ],
        limit=7,
    )
    provides = _clean_list(
        [
            financial.investment_thesis_contribution,
            financial.m_and_a_financial_assessment,
            financial.financing_and_debt_capacity_view,
            *financial.valuation_and_deal_structure_implications,
        ],
        limit=6,
    )
    return AgentContribution(
        agent_name="financial_agent",
        label=AGENT_LABELS["financial_agent"],
        summary=financial.executive_summary,
        provides_to_final_solution=provides,
        key_findings=key_findings,
        citations=_financial_citations(financial),
        confidence=financial.overall_confidence,
    )


def _risk_contribution(risk: RiskAnalysis) -> AgentContribution:
    key_findings = _clean_list(
        [
            risk.headline,
            risk.acquisition_risk_summary,
            risk.integration_risk_view,
            *[item.title for item in risk.top_risks],
            *[item.title for item in risk.deal_breaker_risks],
            *[factor.finding for factor in risk.acquisition_risk_factors],
        ],
        limit=7,
    )
    provides = _clean_list(
        [
            risk.acquisition_risk_summary,
            risk.regulatory_approval_view,
            risk.cyber_data_privacy_view,
            *risk.valuation_and_terms_implications,
            *risk.purchase_agreement_implications,
        ],
        limit=6,
    )
    return AgentContribution(
        agent_name="risk_agent",
        label=AGENT_LABELS["risk_agent"],
        summary=risk.executive_summary,
        provides_to_final_solution=provides,
        key_findings=key_findings,
        citations=_risk_citations(risk),
        confidence=risk.overall_confidence,
    )


def _memo_contribution(memo: InvestmentMemo) -> AgentContribution:
    provides = _clean_list(
        [
            memo.recommendation_rationale,
            memo.decision_framework,
            memo.valuation_and_structure_view,
            *memo.investment_committee_conditions,
        ],
        limit=6,
    )
    key_findings = _clean_list(
        [
            memo.headline,
            memo.buyer_target_fit_view,
            memo.market_view,
            memo.financial_view,
            memo.risk_view,
        ],
        limit=6,
    )
    return AgentContribution(
        agent_name="memo_agent",
        label=AGENT_LABELS["memo_agent"],
        summary=memo.executive_summary,
        provides_to_final_solution=provides,
        key_findings=key_findings,
        citations=_memo_citations(memo),
        confidence=memo.overall_confidence,
    )


def _section_citations(
    contributions: list[AgentContribution],
    agent_names: set[AgentName],
    limit: int = 5,
) -> list[ReportCitation]:
    citations = [
        citation
        for contribution in contributions
        if contribution.agent_name in agent_names
        for citation in contribution.citations
    ]
    return _dedupe_citations(citations, limit=limit)


def build_report_package(
    plan: OrchestrationPlan,
    market: MarketAnalysis,
    financial: FinancialAnalysis,
    risk: RiskAnalysis,
    memo: InvestmentMemo,
) -> ReportPackage:
    contributions = [
        _market_contribution(market),
        _financial_contribution(financial),
        _risk_contribution(risk),
        _memo_contribution(memo),
    ]

    sections = [
        ReportSection(
            title="Executive Summary",
            summary=memo.executive_summary,
            bullets=_clean_list(
                [
                    memo.recommendation_rationale,
                    memo.decision_framework,
                    memo.buyer_target_fit_view,
                    f"Workflow rationale: {plan.cfo_rationale}" if plan.cfo_rationale else "",
                ],
                limit=4,
            ),
            source_agents=["memo_agent", "market_agent", "financial_agent", "risk_agent"],
            citations=_section_citations(
                contributions,
                {"memo_agent", "market_agent", "financial_agent", "risk_agent"},
            ),
        ),
        ReportSection(
            title="Market Read-Through",
            summary=memo.market_view or market.executive_summary,
            bullets=_clean_list(
                [
                    market.investment_thesis_contribution,
                    market.market_position,
                    market.m_and_a_implications,
                    market.capital_markets_read_through,
                ],
                limit=5,
            ),
            source_agents=["market_agent"],
            citations=_section_citations(contributions, {"market_agent"}),
        ),
        ReportSection(
            title="Financial Support",
            summary=memo.financial_view or financial.executive_summary,
            bullets=_clean_list(
                [
                    financial.m_and_a_financial_assessment,
                    financial.valuation_view,
                    financial.financing_and_debt_capacity_view,
                    *financial.valuation_and_deal_structure_implications,
                ],
                limit=6,
            ),
            source_agents=["financial_agent"],
            citations=_section_citations(contributions, {"financial_agent"}),
        ),
        ReportSection(
            title="Risk and Diligence Gates",
            summary=memo.risk_view or risk.executive_summary,
            bullets=_clean_list(
                [
                    risk.acquisition_risk_summary,
                    risk.integration_risk_view,
                    *risk.diligence_priorities,
                    *memo.investment_committee_conditions,
                ],
                limit=7,
            ),
            source_agents=["risk_agent", "memo_agent"],
            citations=_section_citations(contributions, {"risk_agent", "memo_agent"}),
        ),
        ReportSection(
            title="Next Steps and Open Questions",
            summary="Workplan items that must be resolved before stronger recommendation confidence.",
            bullets=_clean_list(
                [
                    *memo.next_diligence_steps,
                    *memo.open_questions,
                    *financial.diligence_questions,
                    *risk.missing_information,
                    *market.missing_information,
                ],
                limit=8,
            ),
            source_agents=["memo_agent", "financial_agent", "risk_agent", "market_agent"],
            citations=_section_citations(
                contributions,
                {"memo_agent", "financial_agent", "risk_agent", "market_agent"},
            ),
        ),
    ]

    source_register = _dedupe_citations(
        [citation for contribution in contributions for citation in contribution.citations]
    )

    return ReportPackage(
        title=memo.headline or "Bastion Investment Committee Report",
        recommendation=memo.recommendation,
        executive_summary=memo.executive_summary,
        agent_contributions=contributions,
        sections=sections,
        source_register=source_register,
        source_limitations=_clean_list(
            [
                *memo.source_limitations,
                *market.missing_information,
                *financial.missing_information,
                *risk.missing_information,
            ],
            limit=10,
        ),
    )
