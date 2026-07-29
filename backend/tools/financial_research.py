from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from tools.market_research import QuoteSnapshot, extract_tickers, fetch_quote_snapshot


MONEY_VALUE = r"\$?\s?\d+(?:,\d{3})*(?:\.\d+)?\s?(?:k|m|mm|million|b|bn|billion)?"

FINANCIAL_LABELS = (
    "ARR",
    "revenue",
    "net revenue",
    "gross profit",
    "gross margin",
    "EBITDA",
    "operating income",
    "net income",
    "cash",
    "debt",
    "runway",
    "burn",
    "monthly burn",
    "enterprise value",
    "equity value",
    "valuation",
)

MONEY_AFTER_LABEL_PATTERN = re.compile(
    rf"(?P<label>{'|'.join(re.escape(label) for label in FINANCIAL_LABELS)})"
    rf"\s*(?:of|is|was|were|at|:|=)?\s*(?P<value>{MONEY_VALUE})",
    flags=re.IGNORECASE,
)

MONEY_BEFORE_LABEL_PATTERN = re.compile(
    rf"(?P<value>{MONEY_VALUE})\s+"
    rf"(?P<label>{'|'.join(re.escape(label) for label in FINANCIAL_LABELS)})",
    flags=re.IGNORECASE,
)

PERCENT_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)%\s+"
    r"(?P<label>gross margin|EBITDA margin|revenue growth|growth|churn|retention|NRR|GRR)",
    flags=re.IGNORECASE,
)

PERCENT_AFTER_LABEL_PATTERN = re.compile(
    r"(?P<label>gross margin|EBITDA margin|revenue growth|growth|churn|retention|NRR|GRR)"
    r"\s*(?:of|is|was|were|at|:|=)?\s*(?P<value>\d+(?:\.\d+)?)%",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class FinancialMetricSignal:
    metric: str
    value: str
    source: str
    excerpt: str
    confidence: str


@dataclass(frozen=True)
class FinancialCalculation:
    name: str
    value: str
    formula: str
    source_metrics: list[str]
    confidence: str


@dataclass(frozen=True)
class FinancialResearchContext:
    generated_at: str
    extracted_metrics: list[FinancialMetricSignal]
    calculated_metrics: list[FinancialCalculation]
    public_comp_snapshots: list[QuoteSnapshot]
    notes: list[str]
    retrieval_succeeded: bool
    retrieval_errors: list[str]

    def to_prompt_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _context_window(text: str, start: int, end: int, width: int = 90) -> str:
    return " ".join(text[max(0, start - width) : min(len(text), end + width)].split())


def _normalize_metric(label: str) -> str:
    return " ".join(label.lower().split()).replace("nrr", "net revenue retention")


def _parse_money(value: str) -> float | None:
    cleaned = value.lower().replace("$", "").replace(",", "").strip()
    match = re.match(r"(?P<number>\d+(?:\.\d+)?)\s?(?P<suffix>[a-z]+)?", cleaned)
    if not match:
        return None
    number = float(match.group("number"))
    suffix = match.group("suffix") or ""
    if suffix in {"k"}:
        return number * 1_000
    if suffix in {"m", "mm", "million"}:
        return number * 1_000_000
    if suffix in {"b", "bn", "billion"}:
        return number * 1_000_000_000
    return number


def extract_financial_metrics(company_text: str) -> list[FinancialMetricSignal]:
    metrics: list[FinancialMetricSignal] = []
    seen: set[tuple[str, str, str]] = set()
    patterns = [
        MONEY_AFTER_LABEL_PATTERN,
        MONEY_BEFORE_LABEL_PATTERN,
        PERCENT_PATTERN,
        PERCENT_AFTER_LABEL_PATTERN,
    ]

    for pattern in patterns:
        for match in pattern.finditer(company_text):
            metric = _normalize_metric(match.group("label"))
            value = " ".join(match.group("value").split())
            if "%" in match.group(0) and not value.endswith("%"):
                value = f"{value}%"
            excerpt = _context_window(company_text, match.start(), match.end())
            key = (metric, value, excerpt)
            if key in seen:
                continue
            seen.add(key)
            metrics.append(
                FinancialMetricSignal(
                    metric=metric,
                    value=value,
                    source="provided company context",
                    excerpt=excerpt,
                    confidence="high",
                )
            )

    return metrics[:30]


def _first_metric_value(
    metrics: list[FinancialMetricSignal],
    names: set[str],
) -> tuple[str, float] | None:
    for metric in metrics:
        if metric.metric not in names:
            continue
        parsed = _parse_money(metric.value)
        if parsed is not None:
            return metric.value, parsed
    return None


def calculate_financial_metrics(
    metrics: list[FinancialMetricSignal],
) -> list[FinancialCalculation]:
    calculations: list[FinancialCalculation] = []
    cash = _first_metric_value(metrics, {"cash"})
    monthly_burn = _first_metric_value(metrics, {"monthly burn", "burn"})

    if cash and monthly_burn and monthly_burn[1] > 0:
        runway_months = cash[1] / monthly_burn[1]
        calculations.append(
            FinancialCalculation(
                name="estimated runway",
                value=f"{runway_months:.1f} months",
                formula="cash / monthly burn",
                source_metrics=[f"cash={cash[0]}", f"monthly burn={monthly_burn[0]}"],
                confidence="medium",
            )
        )

    return calculations


def build_financial_research_context(company_text: str) -> FinancialResearchContext:
    metrics = extract_financial_metrics(company_text)
    calculations = calculate_financial_metrics(metrics)
    tickers = extract_tickers(company_text)
    with ThreadPoolExecutor(max_workers=8) as executor:
        public_comp_snapshots = list(
            executor.map(
                lambda ticker: fetch_quote_snapshot(
                    ticker,
                    "explicit public comparable or company ticker",
                ),
                tickers[:8],
            )
        )
    retrieval_errors = [
        f"{snapshot.ticker}: {snapshot.error}"
        for snapshot in public_comp_snapshots
        if snapshot.error
    ]

    return FinancialResearchContext(
        generated_at=datetime.now(UTC).isoformat(),
        extracted_metrics=metrics,
        calculated_metrics=calculations,
        public_comp_snapshots=public_comp_snapshots,
        notes=[
            "Extracted metrics come from provided company context and should be verified against source documents.",
            "Calculated metrics are simple deterministic calculations from extracted values.",
            "Public comp snapshots are current market context only; they are not a full valuation model.",
        ],
        retrieval_succeeded=(
            not public_comp_snapshots
            or any(snapshot.error is None for snapshot in public_comp_snapshots)
        ),
        retrieval_errors=retrieval_errors,
    )
