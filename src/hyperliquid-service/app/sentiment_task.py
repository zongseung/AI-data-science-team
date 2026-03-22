"""Scheduled sentiment analysis task.

Runs periodically (every 6 hours) to:
1. Fetch crypto news from RSS feeds via news_collector.
2. Analyze sentiment using CryptoSentimentAnalyzer.
3. Save individual article results and per-coin summaries to Supabase.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

from .config import hl_settings
from .news_collector import fetch_news
from .storage import hl_storage

# Import NLP module - in Docker it's at /app/nlp/, locally via sys.path
try:
    from nlp.sentiment_scorer import CryptoSentimentAnalyzer
except ImportError:
    import sys
    _shared_path = str(Path(__file__).resolve().parents[2] / "shared")
    if _shared_path not in sys.path:
        sys.path.insert(0, _shared_path)
    from nlp.sentiment_scorer import CryptoSentimentAnalyzer

logger = structlog.get_logger()
log = logger.bind(component="sentiment_task")

# How often the task runs (seconds)
SENTIMENT_INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours

# Tables
TABLE_NEWS = "crypto_news"
TABLE_SUMMARY = "crypto_sentiment_summary"


async def _save_articles(
    articles_with_sentiment: list[dict[str, Any]],
) -> int:
    """Save analyzed articles to Supabase, skipping duplicates."""
    saved = 0
    client = hl_storage.client

    for article in articles_with_sentiment:
        try:
            record = {
                "coin": article["coin"],
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
            client.table(TABLE_NEWS).upsert(
                record, on_conflict="url"
            ).execute()
            saved += 1

        except Exception as exc:
            log.debug(
                "article_save_skip",
                title=article.get("title", "")[:50],
                error=str(exc),
            )

    return saved


async def _save_summary(
    coin: str,
    period_start: datetime,
    period_end: datetime,
    batch_result: dict[str, Any],
) -> None:
    """Save or update the sentiment summary for a coin and period."""
    client = hl_storage.client

    record = {
        "coin": coin,
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
        client.table(TABLE_SUMMARY).upsert(
            record, on_conflict="coin,period_start"
        ).execute()
        log.info(
            "summary_saved",
            coin=coin,
            avg_sentiment=batch_result["avg_compound"],
            articles=batch_result["article_count"],
        )
    except Exception as exc:
        log.error("summary_save_error", coin=coin, error=str(exc))


async def run_sentiment_analysis() -> dict[str, Any]:
    """Execute a single round of sentiment analysis.

    Returns
    -------
    Dict with per-coin results and total counts.
    """
    # hl_settings.coins는 WS 구독용 (BTC,ETH,SOL).
    # 뉴스 분석은 HYPE도 포함.
    coins = list(set(hl_settings.coins + ["HYPE"]))
    log.info("sentiment_analysis_start", coins=coins)

    # 1. Fetch news
    try:
        articles = await fetch_news(coins=coins, max_articles=200)
    except Exception as exc:
        log.error("news_fetch_failed", error=str(exc))
        return {"error": str(exc), "articles_fetched": 0}

    if not articles:
        log.info("no_articles_found")
        return {"articles_fetched": 0, "coins_analyzed": 0}

    log.info("articles_fetched", count=len(articles))

    # 2. Initialize analyzer
    analyzer = CryptoSentimentAnalyzer()

    # 3. Group articles by coin
    coin_articles: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        coin = article["coin"]
        coin_articles.setdefault(coin, []).append(article)

    # 4. Analyze per-coin batches
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=6)
    period_end = now
    total_saved = 0
    results: dict[str, Any] = {}

    for coin, coin_arts in coin_articles.items():
        log.info("analyzing_coin", coin=coin, articles=len(coin_arts))

        batch_result = analyzer.analyze_batch(coin_arts)
        batch_dict = batch_result.to_dict()

        # Enrich articles with sentiment data for storage
        enriched: list[dict[str, Any]] = []
        for orig, analyzed in zip(coin_arts, batch_result.articles):
            enriched.append({
                **orig,
                "sentiment_score": analyzed.compound_score,
                "sentiment_label": analyzed.label,
                "keywords": analyzed.keywords,
            })

        # 5. Save to Supabase
        try:
            saved = await _save_articles(enriched)
            total_saved += saved
        except Exception as exc:
            log.error("articles_save_error", coin=coin, error=str(exc))

        try:
            await _save_summary(coin, period_start, period_end, batch_dict)
        except Exception as exc:
            log.error("summary_save_error", coin=coin, error=str(exc))

        results[coin] = {
            "article_count": batch_dict["article_count"],
            "avg_sentiment": batch_dict["avg_compound"],
            "label": batch_dict["overall_label"],
        }

    summary = {
        "articles_fetched": len(articles),
        "articles_saved": total_saved,
        "coins_analyzed": len(results),
        "results": results,
    }
    log.info("sentiment_analysis_complete", **summary)
    return summary


async def sentiment_loop() -> None:
    """Background loop: run sentiment analysis on startup, then every 6 hours."""
    log.info("sentiment_loop_starting", interval_hours=SENTIMENT_INTERVAL_SECONDS / 3600)

    # Run immediately on startup
    try:
        await run_sentiment_analysis()
    except Exception as exc:
        log.error("initial_sentiment_run_failed", error=str(exc))

    # Then run periodically
    while True:
        await asyncio.sleep(SENTIMENT_INTERVAL_SECONDS)
        try:
            await run_sentiment_analysis()
        except Exception as exc:
            log.error("sentiment_run_failed", error=str(exc))
