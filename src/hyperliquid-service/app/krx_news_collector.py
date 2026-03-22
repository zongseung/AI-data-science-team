"""KRX stock news collector using free RSS feeds.

Fetches articles from Google News RSS (Korean), Hankyung, MK, and Yonhap RSS
feeds, parses XML, and filters by stock name keywords. No API keys required.
"""

from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx
import structlog

logger = structlog.get_logger()
log = logger.bind(component="krx_news_collector")

# Secondary RSS feeds (general Korean financial news, needs keyword filtering)
KOREAN_RSS_FEEDS: list[dict[str, str]] = [
    {"name": "한국경제", "url": "https://www.hankyung.com/feed/all-news"},
    {"name": "매일경제", "url": "https://www.mk.co.kr/rss/30000001/"},
    {"name": "연합뉴스", "url": "https://www.yna.co.kr/rss/economy.xml"},
]


def _google_news_url(stock_name: str) -> str:
    """Build Google News RSS URL for a Korean stock query."""
    query = quote(f"{stock_name} 주가")
    return (
        f"https://news.google.com/rss/search?"
        f"q={query}&hl=ko&gl=KR&ceid=KR:ko"
    )


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
        pass

    # Fallback: Korean date patterns like "2026.03.22 14:30"
    korean_patterns = [
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d",
    ]
    for pattern in korean_patterns:
        try:
            dt = datetime.strptime(date_str.strip(), pattern)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

    return None


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_google_news_xml(
    xml_text: str,
    stock_name: str,
    stock_code: str,
) -> list[dict[str, Any]]:
    """Parse Google News RSS XML and extract articles.

    Google News RSS returns articles already filtered by the query,
    so we don't need keyword matching.
    """
    articles: list[dict[str, Any]] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        log.warning("xml_parse_error", source="GoogleNews", stock=stock_name)
        return articles

    for item in root.findall(".//item"):
        try:
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pubdate_el = item.find("pubDate")
            source_el = item.find("source")

            title = (title_el.text or "").strip() if title_el is not None else ""
            description = (desc_el.text or "").strip() if desc_el is not None else ""
            url = (link_el.text or "").strip() if link_el is not None else ""
            pub_str = (pubdate_el.text or "").strip() if pubdate_el is not None else ""
            source_name = (source_el.text or "GoogleNews").strip() if source_el is not None else "GoogleNews"

            if not title:
                continue

            # 프리미엄콘텐츠, 광고성 기사 제외
            skip_keywords = ["프리미엄콘텐츠", "프리미엄 콘텐츠", "광고]", "[AD]"]
            if any(kw in title for kw in skip_keywords):
                continue
            if any(kw in (source_name or "") for kw in skip_keywords):
                continue

            published_at = _parse_rfc2822_date(pub_str) if pub_str else None
            description = _strip_html(description)

            articles.append({
                "title": title,
                "description": description[:1000] if description else "",
                "source": source_name,
                "url": url,
                "published_at": published_at.isoformat() if published_at else None,
                "stock_name": stock_name,
                "stock_code": stock_code,
            })

        except Exception:
            log.debug("item_parse_skip", source="GoogleNews", stock=stock_name)
            continue

    return articles


def _parse_korean_rss_xml(
    xml_text: str,
    source_name: str,
    stock_names: list[str],
    stock_code_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Parse Korean financial RSS XML and filter by stock name keywords.

    Handles both standard RSS 2.0 <item> and Atom <entry> elements.
    """
    articles: list[dict[str, Any]] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        log.warning("xml_parse_error", source=source_name)
        return articles

    atom_ns = "{http://www.w3.org/2005/Atom}"

    items = root.findall(".//item")
    if not items:
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

            # Match against target stock names
            searchable = f"{title} {description}"
            matched_stock = None
            for stock_name in stock_names:
                if stock_name in searchable:
                    matched_stock = stock_name
                    break

            if matched_stock is None:
                continue

            published_at = _parse_rfc2822_date(pub_str) if pub_str else None
            description = _strip_html(description)

            articles.append({
                "title": title,
                "description": description[:1000] if description else "",
                "source": source_name,
                "url": url,
                "published_at": published_at.isoformat() if published_at else None,
                "stock_name": matched_stock,
                "stock_code": stock_code_map.get(matched_stock, ""),
            })

        except Exception:
            log.debug("item_parse_skip", source=source_name)
            continue

    return articles


async def fetch_krx_news(
    stock_names: list[str],
    stock_code_map: dict[str, str] | None = None,
    max_per_stock: int = 30,
) -> list[dict[str, Any]]:
    """Fetch KRX stock news from RSS feeds and filter by stock keywords.

    Parameters
    ----------
    stock_names:
        List of Korean stock names (e.g. ["삼성전자", "SK하이닉스"]).
    stock_code_map:
        Optional mapping of stock_name -> stock_code. If not provided,
        stock_code will be empty.
    max_per_stock:
        Maximum number of articles per stock to return.

    Returns
    -------
    List of article dicts with keys: title, description, source, url,
    published_at, stock_name, stock_code.
    """
    if stock_code_map is None:
        stock_code_map = {}

    all_articles: list[dict[str, Any]] = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(20.0),
        follow_redirects=True,
        headers={
            "User-Agent": "KRXNewsFetcher/1.0 (RSS Reader)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        },
    ) as client:

        async def _fetch_google_news(stock_name: str) -> list[dict[str, Any]]:
            """Fetch Google News RSS for a single stock."""
            url = _google_news_url(stock_name)
            stock_code = stock_code_map.get(stock_name, "")
            try:
                log.info("fetching_google_news", stock=stock_name, url=url)
                response = await client.get(url)
                response.raise_for_status()
                articles = _parse_google_news_xml(
                    response.text, stock_name=stock_name, stock_code=stock_code,
                )
                log.info(
                    "google_news_parsed",
                    stock=stock_name,
                    total_matched=len(articles),
                )
                return articles[:max_per_stock]
            except httpx.HTTPStatusError as exc:
                log.warning(
                    "google_news_http_error",
                    stock=stock_name,
                    status=exc.response.status_code,
                )
            except httpx.RequestError as exc:
                log.warning(
                    "google_news_request_error",
                    stock=stock_name,
                    error=str(exc),
                )
            except Exception as exc:
                log.error(
                    "google_news_unexpected_error",
                    stock=stock_name,
                    error=str(exc),
                )
            return []

        async def _fetch_korean_rss(feed: dict[str, str]) -> list[dict[str, Any]]:
            """Fetch and parse a single Korean RSS feed, filtering by stock names."""
            try:
                log.info("fetching_korean_rss", source=feed["name"], url=feed["url"])
                response = await client.get(feed["url"])
                response.raise_for_status()
                articles = _parse_korean_rss_xml(
                    response.text,
                    source_name=feed["name"],
                    stock_names=stock_names,
                    stock_code_map=stock_code_map,
                )
                log.info(
                    "korean_rss_parsed",
                    source=feed["name"],
                    total_matched=len(articles),
                )
                return articles
            except httpx.HTTPStatusError as exc:
                log.warning(
                    "korean_rss_http_error",
                    source=feed["name"],
                    status=exc.response.status_code,
                )
            except httpx.RequestError as exc:
                log.warning(
                    "korean_rss_request_error",
                    source=feed["name"],
                    error=str(exc),
                )
            except Exception as exc:
                log.error(
                    "korean_rss_unexpected_error",
                    source=feed["name"],
                    error=str(exc),
                )
            return []

        # Parallel fetch: Google News per stock + Korean RSS feeds
        tasks = [_fetch_google_news(name) for name in stock_names]
        tasks.extend(_fetch_korean_rss(feed) for feed in KOREAN_RSS_FEEDS)

        results = await asyncio.gather(*tasks)
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

    # Sort by published_at (newest first)
    unique.sort(
        key=lambda a: a.get("published_at") or "",
        reverse=True,
    )

    # Limit per stock
    stock_counts: dict[str, int] = {}
    limited: list[dict[str, Any]] = []
    for article in unique:
        stock = article.get("stock_name", "")
        count = stock_counts.get(stock, 0)
        if count < max_per_stock:
            limited.append(article)
            stock_counts[stock] = count + 1

    log.info(
        "krx_news_fetch_complete",
        total=len(limited),
        stocks=len(stock_names),
    )
    return limited
