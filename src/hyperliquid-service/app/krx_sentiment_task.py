"""Scheduled KRX stock sentiment analysis task.

Runs periodically (every 6 hours) to:
1. Fetch Korean stock news from RSS feeds via krx_news_collector.
2. Analyze sentiment using KrxSentimentAnalyzer.
3. Save individual article results and per-stock summaries to Supabase.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

from .config import hl_settings
from .storage import hl_storage

# Import KRX news collector - in Docker it's at /app/app/, locally via sys.path
try:
    from .krx_news_collector import fetch_krx_news
except ImportError:
    import sys
    _collector_path = str(
        Path(__file__).resolve().parents[3] / "collection-service" / "app" / "collectors"
    )
    if _collector_path not in sys.path:
        sys.path.insert(0, _collector_path)
    from krx_news_collector import fetch_krx_news

# Import KRX sentiment scorer - in Docker it's at /app/nlp/, locally via sys.path
try:
    from nlp.krx_sentiment_scorer import KrxSentimentAnalyzer
except ImportError:
    import sys
    _shared_path = str(Path(__file__).resolve().parents[2] / "shared")
    if _shared_path not in sys.path:
        sys.path.insert(0, _shared_path)
    from nlp.krx_sentiment_scorer import KrxSentimentAnalyzer

logger = structlog.get_logger()
log = logger.bind(component="krx_sentiment_task")

# How often the task runs (seconds)
KRX_SENTIMENT_INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours

# Tables
TABLE_KRX_NEWS = "krx_news"
TABLE_KRX_SUMMARY = "krx_sentiment_summary"

# Default stocks to track (top 5 by market cap / interest)
DEFAULT_KRX_STOCKS: dict[str, str] = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "NAVER": "035420",
    "카카오": "035720",
    "현대자동차": "005380",
}


async def _save_krx_articles(
    articles_with_sentiment: list[dict[str, Any]],
) -> int:
    """Save analyzed KRX articles to Supabase, skipping duplicates."""
    saved = 0
    client = hl_storage.client

    for article in articles_with_sentiment:
        try:
            record = {
                "stock_code": article["stock_code"],
                "stock_name": article["stock_name"],
                "title": article["title"],
                "description": article.get("description", ""),
                "source": article.get("source", ""),
                "url": article.get("url", ""),
                "published_at": article.get("published_at"),
                "sentiment_score": article["sentiment_score"],
                "sentiment_label": article["sentiment_label"],
                "keywords": article.get("keywords", []),
            }

            # Upsert on URL uniqueness
            client.table(TABLE_KRX_NEWS).upsert(
                record, on_conflict="url"
            ).execute()
            saved += 1

        except Exception as exc:
            log.debug(
                "krx_article_save_skip",
                title=article.get("title", "")[:50],
                error=str(exc),
            )

    return saved


async def _save_krx_summary(
    stock_code: str,
    stock_name: str,
    period_start: datetime,
    period_end: datetime,
    batch_result: dict[str, Any],
) -> None:
    """Save or update the sentiment summary for a stock and period."""
    client = hl_storage.client

    record = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "avg_sentiment": batch_result["avg_compound"],
        "sentiment_label": batch_result["overall_label"],
        "article_count": batch_result["article_count"],
        "positive_count": batch_result["positive_count"],
        "negative_count": batch_result["negative_count"],
        "neutral_count": batch_result["neutral_count"],
        "top_keywords": batch_result["top_keywords"],
    }

    try:
        client.table(TABLE_KRX_SUMMARY).upsert(
            record, on_conflict="stock_code,period_start"
        ).execute()
        log.info(
            "krx_summary_saved",
            stock_code=stock_code,
            stock_name=stock_name,
            avg_sentiment=batch_result["avg_compound"],
            articles=batch_result["article_count"],
        )
    except Exception as exc:
        log.error(
            "krx_summary_save_error",
            stock_code=stock_code,
            error=str(exc),
        )


async def run_krx_sentiment(
    stock_names: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a single round of KRX stock sentiment analysis.

    Parameters
    ----------
    stock_names:
        List of Korean stock names. Defaults to DEFAULT_KRX_STOCKS.

    Returns
    -------
    Dict with per-stock results and total counts.
    """
    if stock_names is None:
        stock_names = list(DEFAULT_KRX_STOCKS.keys())

    # Build stock_code_map from defaults + any custom stocks
    stock_code_map: dict[str, str] = {}
    for name in stock_names:
        stock_code_map[name] = DEFAULT_KRX_STOCKS.get(name, "")

    log.info("krx_sentiment_analysis_start", stocks=stock_names)

    # 1. Fetch news
    try:
        articles = await fetch_krx_news(
            stock_names=stock_names,
            stock_code_map=stock_code_map,
            max_per_stock=30,
        )
    except Exception as exc:
        log.error("krx_news_fetch_failed", error=str(exc))
        return {"error": str(exc), "articles_fetched": 0}

    if not articles:
        log.info("no_krx_articles_found")
        return {"articles_fetched": 0, "stocks_analyzed": 0}

    log.info("krx_articles_fetched", count=len(articles))

    # 2. Initialize analyzer
    analyzer = KrxSentimentAnalyzer()

    # 3. Group articles by stock_name
    stock_articles: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        stock = article["stock_name"]
        stock_articles.setdefault(stock, []).append(article)

    # 4. Analyze per-stock batches
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=6)
    period_end = now
    total_saved = 0
    results: dict[str, Any] = {}

    for stock_name, stock_arts in stock_articles.items():
        stock_code = stock_code_map.get(stock_name, "")
        log.info(
            "analyzing_krx_stock",
            stock_name=stock_name,
            stock_code=stock_code,
            articles=len(stock_arts),
        )

        batch_result = analyzer.analyze_krx_batch(stock_arts, stock_name=stock_name)
        batch_dict = batch_result.to_dict()

        # Enrich articles with sentiment data for storage
        enriched: list[dict[str, Any]] = []
        for orig, analyzed in zip(stock_arts, batch_result.articles):
            enriched.append({
                **orig,
                "sentiment_score": analyzed.compound_score,
                "sentiment_label": analyzed.label,
                "keywords": analyzed.keywords,
            })

        # 5. Save to Supabase
        try:
            saved = await _save_krx_articles(enriched)
            total_saved += saved
        except Exception as exc:
            log.error(
                "krx_articles_save_error",
                stock_name=stock_name,
                error=str(exc),
            )

        try:
            await _save_krx_summary(
                stock_code, stock_name, period_start, period_end, batch_dict,
            )
        except Exception as exc:
            log.error(
                "krx_summary_save_error",
                stock_name=stock_name,
                error=str(exc),
            )

        results[stock_name] = {
            "stock_code": stock_code,
            "article_count": batch_dict["article_count"],
            "avg_sentiment": batch_dict["avg_compound"],
            "label": batch_dict["overall_label"],
        }

    summary = {
        "articles_fetched": len(articles),
        "articles_saved": total_saved,
        "stocks_analyzed": len(results),
        "results": results,
    }
    log.info("krx_sentiment_analysis_complete", **summary)
    return summary


async def krx_sentiment_loop() -> None:
    """Background loop: run KRX sentiment analysis on startup, then every 6 hours."""
    log.info(
        "krx_sentiment_loop_starting",
        interval_hours=KRX_SENTIMENT_INTERVAL_SECONDS / 3600,
    )

    # Run immediately on startup
    try:
        await run_krx_sentiment()
    except Exception as exc:
        log.error("initial_krx_sentiment_run_failed", error=str(exc))

    # Then run periodically
    while True:
        await asyncio.sleep(KRX_SENTIMENT_INTERVAL_SECONDS)
        try:
            await run_krx_sentiment()
        except Exception as exc:
            log.error("krx_sentiment_run_failed", error=str(exc))
