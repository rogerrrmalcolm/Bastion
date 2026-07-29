from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REQUEST_TIMEOUT_SECONDS = 8
MAX_NEWS_ITEMS_PER_QUERY = 4
MAX_TOTAL_NEWS_ITEMS = 12

TICKER_PATTERN = re.compile(
    r"(?:\$|ticker[:\s]+|NYSE[:\s]+|NASDAQ[:\s]+|Nasdaq[:\s]+)([A-Z][A-Z0-9.-]{0,5})"
)

STOP_TICKERS = {
    "AI",
    "ARR",
    "CFO",
    "CEO",
    "EBITDA",
    "EV",
    "IPO",
    "LTM",
    "M",
    "M&A",
    "PE",
    "SaaS",
}

SECTOR_PROXY_KEYWORDS = {
    "ai": ["QQQ", "IGV"],
    "software": ["IGV", "QQQ"],
    "saas": ["IGV", "QQQ"],
    "technology": ["QQQ", "IGV"],
    "healthcare": ["XLV"],
    "biotech": ["XBI", "XLV"],
    "financial": ["XLF"],
    "bank": ["XLF"],
    "consumer": ["XLY", "XLP"],
    "retail": ["XRT", "XLY"],
    "energy": ["XLE"],
    "oil": ["XLE", "USO"],
    "industrial": ["XLI"],
    "manufacturing": ["XLI"],
    "real estate": ["XLRE"],
    "semiconductor": ["SMH", "QQQ"],
}

DEAL_PROXY_TICKERS = {
    "SPY": "U.S. equity risk appetite",
    "QQQ": "growth and technology valuation sentiment",
    "IWM": "SMID-cap buyer and sponsor risk appetite",
    "HYG": "high-yield financing conditions",
    "LQD": "investment-grade credit conditions",
}


@dataclass(frozen=True)
class QuoteSnapshot:
    ticker: str
    source: str
    source_url: str
    description: str
    currency: str | None
    exchange: str | None
    latest_price: float | None
    previous_close: float | None
    one_month_change_pct: float | None
    ytd_change_pct: float | None
    one_year_change_pct: float | None
    as_of: str | None
    error: str | None = None


@dataclass(frozen=True)
class NewsSearchResult:
    query: str
    title: str
    source: str | None
    published_at: str | None
    url: str
    relevance: str


@dataclass(frozen=True)
class MarketResearchContext:
    generated_at: str
    target_company: str | None
    detected_tickers: list[str]
    market_proxy_tickers: dict[str, str]
    search_queries: list[str]
    quote_snapshots: list[QuoteSnapshot]
    news_results: list[NewsSearchResult]
    notes: list[str]
    retrieval_succeeded: bool
    retrieval_errors: list[str]

    def to_prompt_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_xml(url: str) -> ET.Element:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return ET.fromstring(response.read())


def _pct_change(start: float | None, end: float | None) -> float | None:
    if start in (None, 0) or end is None:
        return None
    return round(((end - start) / start) * 100, 2)


def _first_close_on_or_after(
    timestamps: list[int],
    closes: list[float | None],
    target_year: int,
) -> float | None:
    for timestamp, close in zip(timestamps, closes, strict=False):
        if close is None:
            continue
        if datetime.fromtimestamp(timestamp, UTC).year >= target_year:
            return close
    return None


def _latest_valid_close(closes: list[float | None]) -> float | None:
    for close in reversed(closes):
        if close is not None:
            return close
    return None


def _first_valid_close(closes: list[float | None]) -> float | None:
    for close in closes:
        if close is not None:
            return close
    return None


def _close_n_points_back(closes: list[float | None], points_back: int) -> float | None:
    valid_closes = [close for close in closes if close is not None]
    if len(valid_closes) <= points_back:
        return None
    return valid_closes[-points_back - 1]


def fetch_quote_snapshot(ticker: str, description: str) -> QuoteSnapshot:
    source_url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{ticker}?range=1y&interval=1d"
    )
    try:
        payload = _fetch_json(source_url)
        result = payload["chart"]["result"][0]
        meta = result.get("meta", {})
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        timestamps = result.get("timestamp", [])
        closes = quote.get("close", [])
        latest_price = meta.get("regularMarketPrice") or _latest_valid_close(closes)
        previous_close = meta.get("chartPreviousClose")
        one_month_close = _close_n_points_back(closes, 21)
        one_year_close = _first_valid_close(closes)
        ytd_close = _first_close_on_or_after(
            timestamps,
            closes,
            datetime.now(UTC).year,
        )
        as_of = None
        if meta.get("regularMarketTime"):
            as_of = datetime.fromtimestamp(meta["regularMarketTime"], UTC).isoformat()

        return QuoteSnapshot(
            ticker=ticker,
            source="Yahoo Finance chart endpoint",
            source_url=source_url,
            description=description,
            currency=meta.get("currency"),
            exchange=meta.get("exchangeName") or meta.get("fullExchangeName"),
            latest_price=round(float(latest_price), 4) if latest_price is not None else None,
            previous_close=(
                round(float(previous_close), 4)
                if previous_close is not None
                else None
            ),
            one_month_change_pct=_pct_change(one_month_close, latest_price),
            ytd_change_pct=_pct_change(ytd_close, latest_price),
            one_year_change_pct=_pct_change(one_year_close, latest_price),
            as_of=as_of,
        )
    except Exception as error:
        return QuoteSnapshot(
            ticker=ticker,
            source="Yahoo Finance chart endpoint",
            source_url=source_url,
            description=description,
            currency=None,
            exchange=None,
            latest_price=None,
            previous_close=None,
            one_month_change_pct=None,
            ytd_change_pct=None,
            one_year_change_pct=None,
            as_of=None,
            error=str(error),
        )


def search_google_news_with_status(
    query: str,
    relevance: str,
) -> tuple[list[NewsSearchResult], str | None]:
    url = "https://news.google.com/rss/search?" + urlencode(
        {
            "q": query,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
    )
    results: list[NewsSearchResult] = []
    try:
        root = _fetch_xml(url)
    except Exception as error:
        return results, f"{query}: {type(error).__name__}: {error}"

    for item in root.findall("./channel/item")[:MAX_NEWS_ITEMS_PER_QUERY]:
        source = item.find("source")
        source_name = source.text if source is not None else None
        results.append(
            NewsSearchResult(
                query=query,
                title=item.findtext("title") or "",
                source=source_name,
                published_at=item.findtext("pubDate"),
                url=item.findtext("link") or url,
                relevance=relevance,
            )
        )

    return results, None


def search_google_news(query: str, relevance: str) -> list[NewsSearchResult]:
    results, _ = search_google_news_with_status(query, relevance)
    return results


def extract_tickers(company_text: str) -> list[str]:
    tickers = set()
    for match in TICKER_PATTERN.finditer(company_text):
        ticker = match.group(1).upper().strip(".,;:)]}")
        tickers.add(ticker.replace(".", "-"))

    return sorted(ticker for ticker in tickers if ticker not in STOP_TICKERS)


def infer_target_company(company_text: str) -> str | None:
    company_context_match = re.search(
        r"Current company context:\s*(.+?)(?:\n\n|\Z)",
        company_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    search_text = company_context_match.group(1) if company_context_match else company_text
    patterns = [
        r"([A-Z][A-Za-z0-9&.,' -]{1,80}?)\s+is\s+(?:a|an|the)\s+",
        r"target(?: company)?:\s*([A-Z][A-Za-z0-9&.,' -]{1,80})",
        r"company:\s*([A-Z][A-Za-z0-9&.,' -]{1,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, search_text, flags=re.IGNORECASE)
        if match:
            return " ".join(match.group(1).split()).strip(" .,:;")
    return None


def infer_sector_terms(company_text: str) -> list[str]:
    lowered = company_text.lower()
    terms: list[str] = []
    for keyword in SECTOR_PROXY_KEYWORDS:
        if keyword in lowered:
            terms.append(keyword)

    sector_matches = re.findall(
        r"(?:sector|industry|market|vertical)[:\s]+([A-Za-z0-9&/ -]{3,60})",
        company_text,
        flags=re.IGNORECASE,
    )
    for match in sector_matches:
        terms.append(" ".join(match.split()).strip(" .,:;"))

    unique_terms: list[str] = []
    for term in terms:
        if term and term not in unique_terms:
            unique_terms.append(term)
    return unique_terms[:5]


def select_market_proxy_tickers(company_text: str) -> dict[str, str]:
    lowered = company_text.lower()
    proxies = dict(DEAL_PROXY_TICKERS)
    for keyword, tickers in SECTOR_PROXY_KEYWORDS.items():
        if keyword not in lowered:
            continue
        for ticker in tickers:
            proxies.setdefault(ticker, f"{keyword} sector market proxy")
    return proxies


def build_deal_market_queries(company_text: str) -> list[tuple[str, str]]:
    company = infer_target_company(company_text)
    sectors = infer_sector_terms(company_text)
    queries: list[tuple[str, str]] = []

    if company:
        queries.extend(
            [
                (
                    f'"{company}" acquisition OR merger OR M&A OR funding',
                    "direct target or transaction news",
                ),
                (
                    f'"{company}" competitors market share pricing demand',
                    "competitive and demand signals affecting the target",
                ),
                (
                    f'"{company}" regulation litigation customer churn',
                    "risk and regulatory signals affecting diligence",
                ),
            ]
        )

    for sector in sectors[:3]:
        queries.extend(
            [
                (
                    f'"{sector}" M&A valuation multiples deal activity outlook',
                    "sector M&A valuation and buyer appetite",
                ),
                (
                    f'"{sector}" demand outlook pricing margin pressure',
                    "sector demand, pricing, and margin signal",
                ),
                (
                    f'"{sector}" regulation market risk M&A',
                    "sector regulatory and market-risk signal",
                ),
            ]
        )

    if not queries:
        queries.append(
            (
                "M&A valuation multiples financing conditions buyer appetite market outlook",
                "general transaction-market conditions",
            )
        )

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for query, relevance in queries:
        if query in seen:
            continue
        seen.add(query)
        deduped.append((query, relevance))
    return deduped[:6]


def build_market_research_context(company_text: str) -> MarketResearchContext:
    generated_at = datetime.now(UTC).isoformat()
    target_company = infer_target_company(company_text)
    detected_tickers = extract_tickers(company_text)
    proxy_tickers = select_market_proxy_tickers(company_text)
    quote_targets = {
        **{ticker: "explicit public-company ticker from company context" for ticker in detected_tickers},
        **proxy_tickers,
    }
    search_queries = build_deal_market_queries(company_text)

    with ThreadPoolExecutor(max_workers=8) as executor:
        quote_futures = [
            executor.submit(fetch_quote_snapshot, ticker, description)
            for ticker, description in quote_targets.items()
        ]
        news_futures = [
            executor.submit(search_google_news_with_status, query, relevance)
            for query, relevance in search_queries
        ]
        quote_snapshots = [future.result() for future in quote_futures]
        news_attempts = [future.result() for future in news_futures]
        news_results = [
            result
            for results, _ in news_attempts
            for result in results
        ][:MAX_TOTAL_NEWS_ITEMS]

    retrieval_errors = [
        f"{snapshot.ticker}: {snapshot.error}"
        for snapshot in quote_snapshots
        if snapshot.error
    ]
    retrieval_errors.extend(
        error
        for _, error in news_attempts
        if error
    )
    quote_retrieval_succeeded = any(
        snapshot.error is None for snapshot in quote_snapshots
    )
    news_retrieval_succeeded = any(
        error is None for _, error in news_attempts
    )

    notes = [
        "News results come from Google News RSS and should be treated as current search context, not a full diligence file.",
        "Quote snapshots use no-key public Yahoo Finance chart data and may be unavailable for private companies or unsupported symbols.",
        "Deal proxy tickers are market indicators for valuation, financing, and buyer appetite; they are not company-specific evidence unless the ticker was provided in the company context.",
    ]

    return MarketResearchContext(
        generated_at=generated_at,
        target_company=target_company,
        detected_tickers=detected_tickers,
        market_proxy_tickers=proxy_tickers,
        search_queries=[query for query, _ in search_queries],
        quote_snapshots=quote_snapshots,
        news_results=news_results,
        notes=notes,
        retrieval_succeeded=(
            quote_retrieval_succeeded or news_retrieval_succeeded
        ),
        retrieval_errors=retrieval_errors,
    )
