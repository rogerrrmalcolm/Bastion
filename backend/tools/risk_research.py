from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from backend.tools.market_research import (
    NewsSearchResult,
    build_deal_market_queries,
    infer_sector_terms,
    infer_target_company,
    search_google_news,
)


RISK_KEYWORDS = {
    "commercial": [
        "customer concentration",
        "concentration",
        "top customer",
        "largest customer",
        "pipeline",
        "churn",
        "retention",
        "renewal",
        "pricing pressure",
    ],
    "customer_concentration": [
        "customer concentration",
        "concentration",
        "top customer",
        "largest customer",
    ],
    "retention": ["churn", "retention", "renewal", "NRR", "GRR", "key customer"],
    "liquidity": ["cash", "burn", "runway", "liquidity", "debt", "covenant"],
    "regulatory": [
        "regulatory",
        "compliance",
        "HIPAA",
        "FDA",
        "SEC",
        "privacy",
        "antitrust",
        "HSR",
        "CFIUS",
        "foreign investment",
        "approval",
    ],
    "legal": [
        "litigation",
        "lawsuit",
        "investigation",
        "settlement",
        "intellectual property",
        "IP",
        "contract dispute",
    ],
    "cybersecurity": [
        "cybersecurity",
        "breach",
        "data security",
        "SOC2",
        "PHI",
        "ransomware",
        "incident response",
    ],
    "data_privacy": ["privacy", "GDPR", "CCPA", "HIPAA", "PHI", "personal data"],
    "integration": [
        "integration",
        "synergy",
        "systems migration",
        "change of control",
        "customer consent",
    ],
    "human_capital": [
        "key person",
        "founder dependency",
        "employee retention",
        "compensation",
        "sales hiring",
    ],
    "governance": ["controls", "governance", "board", "management", "audit"],
    "transaction_process": [
        "exclusivity",
        "earnout",
        "escrow",
        "indemnity",
        "representation",
        "warranty",
    ],
    "market": ["competition", "pricing pressure", "demand", "macro", "recession"],
}


@dataclass(frozen=True)
class InternalRiskSignal:
    category: str
    signal: str
    excerpt: str
    source: str
    confidence: str


@dataclass(frozen=True)
class RiskResearchContext:
    generated_at: str
    internal_risk_signals: list[InternalRiskSignal]
    news_results: list[NewsSearchResult]
    search_queries: list[str]
    notes: list[str]

    def to_prompt_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _context_window(text: str, start: int, end: int, width: int = 110) -> str:
    return " ".join(text[max(0, start - width) : min(len(text), end + width)].split())


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )


def extract_internal_risk_signals(company_text: str) -> list[InternalRiskSignal]:
    signals: list[InternalRiskSignal] = []
    seen: set[tuple[str, str]] = set()
    for category, keywords in RISK_KEYWORDS.items():
        for keyword in keywords:
            pattern = _keyword_pattern(keyword)
            for match in pattern.finditer(company_text):
                excerpt = _context_window(company_text, match.start(), match.end())
                key = (category, excerpt)
                if key in seen:
                    continue
                seen.add(key)
                signals.append(
                    InternalRiskSignal(
                        category=category,
                        signal=keyword,
                        excerpt=excerpt,
                        source="provided company context",
                        confidence="medium",
                    )
                )
    return signals[:25]


def build_risk_search_queries(company_text: str) -> list[tuple[str, str]]:
    company = infer_target_company(company_text)
    sectors = infer_sector_terms(company_text)
    queries: list[tuple[str, str]] = []

    if company:
        queries.extend(
            [
                (
                    f'"{company}" acquisition risk litigation investigation regulatory cybersecurity',
                    "direct company legal, regulatory, and security risk",
                ),
                (
                    f'"{company}" customer churn outage breach compliance change of control',
                    "direct company operating and customer risk",
                ),
                (
                    f'"{company}" merger acquisition antitrust approval lawsuit',
                    "direct acquisition approval and transaction litigation risk",
                ),
            ]
        )

    for sector in sectors[:3]:
        queries.extend(
            [
                (
                    f'"{sector}" M&A regulatory risk antitrust compliance litigation',
                    "sector regulatory and legal risk",
                ),
                (
                    f'"{sector}" M&A cybersecurity breach data privacy risk',
                    "sector cybersecurity and data risk",
                ),
                (
                    f'"{sector}" acquisition integration risk customer retention synergies',
                    "sector integration and synergy risk",
                ),
            ]
        )

    for query, relevance in build_deal_market_queries(company_text)[:2]:
        queries.append((query, f"deal-market risk read-through: {relevance}"))

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for query, relevance in queries:
        if query in seen:
            continue
        seen.add(query)
        deduped.append((query, relevance))
    return deduped[:6]


def build_risk_research_context(company_text: str) -> RiskResearchContext:
    search_queries = build_risk_search_queries(company_text)
    with ThreadPoolExecutor(max_workers=6) as executor:
        search_result_groups = list(
            executor.map(
                lambda query: search_google_news(query[0], query[1])[:3],
                search_queries,
            )
        )
    news_results = [result for group in search_result_groups for result in group][:12]

    return RiskResearchContext(
        generated_at=datetime.now(UTC).isoformat(),
        internal_risk_signals=extract_internal_risk_signals(company_text),
        news_results=news_results,
        search_queries=[query for query, _ in search_queries],
        notes=[
            "Risk search uses current Google News RSS results and is not a substitute for legal, cyber, or regulatory diligence.",
            "Internal risk signals are extracted from the provided company context and should be verified in source materials.",
        ],
    )
