"""Crypto news collector using free RSS feeds.

Fetches articles from CoinDesk and CoinTelegraph RSS feeds, parses XML,
and filters by coin-related keywords. No API keys required.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()
log = logger.bind(component="news_collector")

# RSS feed URLs (free, no API key required)
RSS_FEEDS: list[dict[str, str]] = [
    # Tier 1 — 종합 커버리지 (BTC/ETH/SOL/HYPE 전부)
    {"name": "CoinDesk",      "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "CoinTelegraph",  "url": "https://cointelegraph.com/rss"},
    {"name": "TheBlock",       "url": "https://www.theblock.co/rss.xml"},
    {"name": "CryptoNews",     "url": "https://cryptonews.com/news/feed/"},
    {"name": "U.Today",        "url": "https://u.today/rss"},
    # Tier 2 — BTC/ETH/SOL 중심
    {"name": "Decrypt",        "url": "https://decrypt.co/feed"},
    {"name": "TheDefiant",     "url": "https://thedefiant.io/feed"},
    {"name": "Blockworks",     "url": "https://blockworks.co/feed"},
    {"name": "DailyHodl",      "url": "https://dailyhodl.com/feed/"},
    # Tier 3 — 보조
    {"name": "CryptoSlate",    "url": "https://cryptoslate.com/feed/"},
    {"name": "AMBCrypto",      "url": "https://ambcrypto.com/feed/"},
]

# Common coin aliases for matching
COIN_ALIASES: dict[str, list[str]] = {
    "BTC": ["btc", "bitcoin"],
    "ETH": ["eth", "ethereum", "ether"],
    "SOL": ["sol", "solana"],
    "XRP": ["xrp", "ripple"],
    "ADA": ["ada", "cardano"],
    "DOGE": ["doge", "dogecoin"],
    "AVAX": ["avax", "avalanche"],
    "DOT": ["dot", "polkadot"],
    "LINK": ["link", "chainlink"],
    "MATIC": ["matic", "polygon"],
    "BNB": ["bnb", "binance"],
    "ARB": ["arb", "arbitrum"],
    "OP": ["optimism"],
    "ATOM": ["atom", "cosmos"],
    "UNI": ["uni", "uniswap"],
    "APT": ["apt", "aptos"],
    "SUI": ["sui"],
    "NEAR": ["near"],
    "FTM": ["ftm", "fantom"],
    "INJ": ["inj", "injective"],
    "HYPE": ["hype", "hyperliquid"],
}


def _match_coin(text: str, coins: list[str]) -> str | None:
    """Check if text mentions any of the target coins. Return matched coin or None."""
    text_lower = text.lower()
    for coin in coins:
        coin_upper = coin.upper()
        aliases = COIN_ALIASES.get(coin_upper, [coin.lower()])
        for alias in aliases:
            if alias in text_lower:
                return coin_upper
    return None


def _parse_rfc2822_date(date_str: str) -> datetime | None:
    """Parse RFC 2822 date string (common in RSS) into a timezone-aware datetime."""
    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        pass

    # Fallback: try ISO 8601
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _parse_rss_xml(
    xml_text: str,
    source_name: str,
    coins: list[str],
) -> list[dict[str, Any]]:
    """Parse an RSS XML document and extract articles matching target coins.

    Handles both standard RSS 2.0 ``<item>`` and Atom ``<entry>`` elements
    gracefully, skipping malformed entries.
    """
    articles: list[dict[str, Any]] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        log.warning("xml_parse_error", source=source_name)
        return articles

    # Handle Atom namespace
    atom_ns = "{http://www.w3.org/2005/Atom}"

    # Try RSS 2.0 items first
    items = root.findall(".//item")
    if not items:
        # Try Atom entries
        items = root.findall(f".//{atom_ns}entry")

    for item in items:
        try:
            # RSS 2.0 fields
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pubdate_el = item.find("pubDate")

            # Atom fallbacks
            if title_el is None:
                title_el = item.find(f"{atom_ns}title")
            if desc_el is None:
                desc_el = item.find(f"{atom_ns}summary")
            if link_el is None:
                atom_link = item.find(f"{atom_ns}link")
                link_text = atom_link.get("href", "") if atom_link is not None else ""
            else:
                link_text = (link_el.text or "").strip()
            if pubdate_el is None:
                pubdate_el = item.find(f"{atom_ns}published")
                if pubdate_el is None:
                    pubdate_el = item.find(f"{atom_ns}updated")

            title = (title_el.text or "").strip() if title_el is not None else ""
            description = (desc_el.text or "").strip() if desc_el is not None else ""
            if not isinstance(link_text, str):
                link_text = ""
            url = link_text.strip()
            pub_str = (pubdate_el.text or "").strip() if pubdate_el is not None else ""

            if not title:
                continue

            # Match against target coins
            searchable = f"{title} {description}"
            matched_coin = _match_coin(searchable, coins)
            if matched_coin is None:
                continue

            published_at = _parse_rfc2822_date(pub_str) if pub_str else None

            articles.append({
                "title": title,
                "description": description[:1000] if description else "",
                "source": source_name,
                "url": url,
                "published_at": published_at.isoformat() if published_at else None,
                "coin": matched_coin,
            })

        except Exception:
            log.debug("item_parse_skip", source=source_name)
            continue

    return articles


async def fetch_news(
    coins: list[str],
    max_articles: int = 50,
) -> list[dict[str, Any]]:
    """Fetch crypto news from RSS feeds and filter by coin keywords.

    Parameters
    ----------
    coins:
        List of coin tickers to match (e.g. ``["BTC", "ETH", "SOL"]``).
    max_articles:
        Maximum number of articles to return across all feeds.

    Returns
    -------
    List of article dicts with keys: title, description, source, url,
    published_at, coin.
    """
    all_articles: list[dict[str, Any]] = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        headers={
            "User-Agent": "CryptoNewsFetcher/1.0 (RSS Reader)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    ) as client:

        async def _fetch_one(feed: dict[str, str]) -> list[dict[str, Any]]:
            """단일 피드 fetch + parse (에러 시 빈 리스트)."""
            try:
                log.info("fetching_rss", source=feed["name"], url=feed["url"])
                response = await client.get(feed["url"])
                response.raise_for_status()
                articles = _parse_rss_xml(
                    response.text, source_name=feed["name"], coins=coins,
                )
                log.info("rss_parsed", source=feed["name"], total_matched=len(articles))
                return articles
            except httpx.HTTPStatusError as exc:
                log.warning("rss_http_error", source=feed["name"], status=exc.response.status_code)
            except httpx.RequestError as exc:
                log.warning("rss_request_error", source=feed["name"], error=str(exc))
            except Exception as exc:
                log.error("rss_unexpected_error", source=feed["name"], error=str(exc))
            return []

        # 11개 소스 병렬 fetch
        results = await asyncio.gather(*[_fetch_one(feed) for feed in RSS_FEEDS])
        for articles in results:
            all_articles.extend(articles)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[dict[str, Any]] = []
    for article in all_articles:
        url = article.get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique.append(article)

    # Sort by published_at (newest first) and limit
    unique.sort(
        key=lambda a: a.get("published_at") or "",
        reverse=True,
    )

    log.info("news_fetch_complete", total=len(unique), limit=max_articles)
    return unique[:max_articles]
