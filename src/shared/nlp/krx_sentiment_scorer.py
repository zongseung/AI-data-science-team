"""Korean stock sentiment analysis extending the crypto sentiment base.

Combines the existing TF-IDF + VADER infrastructure from
``CryptoSentimentAnalyzer`` with Korean stock-specific lexicon terms
for domain-accurate sentiment scoring of Korean financial news.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from .sentiment_scorer import (
    ArticleSentiment,
    BatchSentimentResult,
    CryptoSentimentAnalyzer,
    _ensure_nltk_data,
)

logger = structlog.get_logger()
log = logger.bind(component="krx_sentiment_scorer")


class KrxSentimentAnalyzer(CryptoSentimentAnalyzer):
    """TF-IDF keyword extraction + VADER sentiment for Korean stock news.

    Extends ``CryptoSentimentAnalyzer`` with Korean stock-specific
    positive/negative lexicon terms while reusing the core VADER +
    TF-IDF infrastructure.
    """

    # Korean stock-specific positive terms with boost values
    KRX_BULLISH_TERMS: dict[str, float] = {
        "상승": 0.12,
        "급등": 0.15,
        "호재": 0.12,
        "매수": 0.10,
        "신고가": 0.15,
        "실적개선": 0.12,
        "흑자전환": 0.15,
        "목표가상향": 0.12,
        "투자의견매수": 0.12,
        "배당확대": 0.10,
        "호실적": 0.12,
        "사상최대": 0.12,
        "수주": 0.10,
        "성장": 0.08,
        "반등": 0.10,
        "강세": 0.10,
        "돌파": 0.10,
        "수혜": 0.08,
        "기대감": 0.08,
        "outperform": 0.10,
        "buy": 0.10,
        "upgrade": 0.10,
    }

    # Korean stock-specific negative terms with penalty values
    KRX_BEARISH_TERMS: dict[str, float] = {
        "하락": -0.12,
        "급락": -0.15,
        "악재": -0.12,
        "매도": -0.10,
        "신저가": -0.15,
        "실적부진": -0.12,
        "적자전환": -0.15,
        "목표가하향": -0.12,
        "투자의견매도": -0.12,
        "배당축소": -0.10,
        "어닝쇼크": -0.15,
        "리콜": -0.12,
        "소송": -0.10,
        "약세": -0.10,
        "폭락": -0.18,
        "손실": -0.10,
        "부진": -0.10,
        "하회": -0.08,
        "우려": -0.08,
        "underperform": -0.10,
        "sell": -0.10,
        "downgrade": -0.10,
    }

    def __init__(
        self,
        max_features: int = 1000,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> None:
        super().__init__(max_features=max_features, ngram_range=ngram_range)
        self.log = log

    def _apply_krx_adjustment(self, text: str, base_compound: float) -> float:
        """Apply Korean stock-specific sentiment adjustments."""
        text_lower = text.lower()
        adjustment = 0.0

        for term, boost in self.KRX_BULLISH_TERMS.items():
            if term in text_lower:
                adjustment += boost

        for term, penalty in self.KRX_BEARISH_TERMS.items():
            if term in text_lower:
                adjustment += penalty  # penalty is already negative

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, base_compound + adjustment))

    def analyze_krx_article(
        self, title: str, description: str | None = None,
    ) -> ArticleSentiment:
        """Analyze sentiment of a single Korean stock article.

        Uses VADER for the English/basic sentiment, then applies
        Korean stock-specific adjustments on top.
        """
        description = description or ""
        # Strip HTML tags from description
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

        # Weight title more heavily
        combined = f"{title}. {title}. {description}"

        # Base VADER score (handles English portions)
        vader_scores = self._vader.polarity_scores(combined)
        compound = vader_scores["compound"]

        # Apply crypto adjustments (inherited, for any English finance terms)
        compound = self._apply_crypto_adjustment(combined, compound)

        # Apply KRX-specific Korean adjustments
        compound = self._apply_krx_adjustment(combined, compound)

        return ArticleSentiment(
            title=title,
            description=description,
            compound_score=round(compound, 4),
            label=self._classify(compound),
            positive_score=round(vader_scores["pos"], 4),
            negative_score=round(vader_scores["neg"], 4),
            neutral_score=round(vader_scores["neu"], 4),
        )

    def analyze_krx_batch(
        self,
        articles: list[dict[str, Any]],
        stock_name: str | None = None,
    ) -> BatchSentimentResult:
        """Analyze sentiment for a batch of Korean stock articles.

        Parameters
        ----------
        articles:
            List of dicts with at least ``title`` and optionally ``description``.
        stock_name:
            Optional stock name for logging context.

        Returns
        -------
        BatchSentimentResult with per-article scores and aggregate stats.
        """
        if not articles:
            return BatchSentimentResult(
                articles=[],
                avg_compound=0.0,
                overall_label="neutral",
                article_count=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                top_keywords=[],
            )

        results: list[ArticleSentiment] = []
        texts: list[str] = []

        for article in articles:
            title = article.get("title", "")
            desc = article.get("description", "")
            sentiment = self.analyze_krx_article(title, desc)
            results.append(sentiment)
            texts.append(f"{title} {desc}".strip())

        # Extract keywords from the batch
        keywords = self.extract_keywords(texts, top_n=20)
        top_keywords = [
            {"keyword": kw, "score": round(score, 4)}
            for kw, score in keywords.items()
        ]

        # Assign top keywords to each article result
        enriched: list[ArticleSentiment] = []
        for result in results:
            article_text = f"{result.title} {result.description}".lower()
            article_kws = [
                kw for kw in keywords if kw.lower() in article_text
            ][:5]
            enriched.append(
                ArticleSentiment(
                    title=result.title,
                    description=result.description,
                    compound_score=result.compound_score,
                    label=result.label,
                    keywords=article_kws,
                    positive_score=result.positive_score,
                    negative_score=result.negative_score,
                    neutral_score=result.neutral_score,
                )
            )

        # Aggregate
        scores = [r.compound_score for r in enriched]
        avg = sum(scores) / len(scores) if scores else 0.0
        pos_count = sum(1 for r in enriched if r.label == "positive")
        neg_count = sum(1 for r in enriched if r.label == "negative")
        neu_count = sum(1 for r in enriched if r.label == "neutral")

        self.log.info(
            "krx_batch_analyzed",
            stock_name=stock_name or "all",
            article_count=len(enriched),
            avg_sentiment=round(avg, 4),
        )

        return BatchSentimentResult(
            articles=enriched,
            avg_compound=round(avg, 4),
            overall_label=self._classify(avg),
            article_count=len(enriched),
            positive_count=pos_count,
            negative_count=neg_count,
            neutral_count=neu_count,
            top_keywords=top_keywords,
        )
