"""TF-IDF keyword extraction + VADER sentiment analysis for crypto news.

Combines scikit-learn's TfidfVectorizer for keyword extraction with NLTK's
VADER sentiment analyzer, augmented by a crypto-specific lexicon for
domain-accurate sentiment scoring.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()
log = logger.bind(component="sentiment_scorer")


def _ensure_nltk_data() -> None:
    """Download VADER lexicon if not already present."""
    import nltk  # noqa: E402

    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        log.info("downloading_vader_lexicon")
        # Use a writable directory for NLTK data
        nltk_data_dir = os.path.join(os.path.expanduser("~"), "nltk_data")
        os.makedirs(nltk_data_dir, exist_ok=True)
        nltk.download("vader_lexicon", download_dir=nltk_data_dir, quiet=True)

    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        log.info("downloading_punkt_tokenizer")
        nltk_data_dir = os.path.join(os.path.expanduser("~"), "nltk_data")
        os.makedirs(nltk_data_dir, exist_ok=True)
        nltk.download("punkt_tab", download_dir=nltk_data_dir, quiet=True)


@dataclass(frozen=True)
class ArticleSentiment:
    """Sentiment result for a single article."""

    title: str
    description: str
    compound_score: float
    label: str  # "positive", "negative", "neutral"
    keywords: list[str] = field(default_factory=list)
    positive_score: float = 0.0
    negative_score: float = 0.0
    neutral_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "compound_score": self.compound_score,
            "label": self.label,
            "keywords": self.keywords,
            "positive_score": self.positive_score,
            "negative_score": self.negative_score,
            "neutral_score": self.neutral_score,
        }


@dataclass(frozen=True)
class BatchSentimentResult:
    """Aggregated sentiment result for a batch of articles."""

    articles: list[ArticleSentiment]
    avg_compound: float
    overall_label: str
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    top_keywords: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "avg_compound": self.avg_compound,
            "overall_label": self.overall_label,
            "article_count": self.article_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "top_keywords": self.top_keywords,
            "articles": [a.to_dict() for a in self.articles],
        }


class CryptoSentimentAnalyzer:
    """TF-IDF keyword extraction + VADER sentiment for crypto news."""

    # Crypto-specific positive terms with boost values
    BULLISH_TERMS: dict[str, float] = {
        "bullish": 0.15,
        "moon": 0.1,
        "surge": 0.12,
        "rally": 0.12,
        "breakout": 0.1,
        "partnership": 0.1,
        "listing": 0.1,
        "upgrade": 0.1,
        "adoption": 0.1,
        "integration": 0.08,
        "launch": 0.08,
        "gains": 0.1,
        "approval": 0.12,
        "institutional": 0.08,
        "etf": 0.1,
    }

    # Crypto-specific negative terms with penalty values
    BEARISH_TERMS: dict[str, float] = {
        "bearish": -0.15,
        "crash": -0.15,
        "dump": -0.12,
        "hack": -0.15,
        "exploit": -0.15,
        "scam": -0.15,
        "rug pull": -0.2,
        "sec": -0.08,
        "ban": -0.12,
        "liquidation": -0.1,
        "collapse": -0.15,
        "plunge": -0.12,
        "investigation": -0.1,
        "lawsuit": -0.1,
        "fraud": -0.15,
    }

    # Thresholds for sentiment classification
    POSITIVE_THRESHOLD = 0.05
    NEGATIVE_THRESHOLD = -0.05

    def __init__(
        self,
        max_features: int = 1000,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> None:
        _ensure_nltk_data()

        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vader = SentimentIntensityAnalyzer()

        # Augment VADER lexicon with crypto-specific terms
        for term, score in self.BULLISH_TERMS.items():
            self._vader.lexicon[term] = score * 10  # VADER uses ~[-4, 4] scale
        for term, score in self.BEARISH_TERMS.items():
            self._vader.lexicon[term] = score * 10

        self._vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words="english",
            lowercase=True,
        )
        self.log = log

    def _classify(self, score: float) -> str:
        """Classify a compound score into a label."""
        if score >= self.POSITIVE_THRESHOLD:
            return "positive"
        elif score <= self.NEGATIVE_THRESHOLD:
            return "negative"
        return "neutral"

    def _apply_crypto_adjustment(self, text: str, base_compound: float) -> float:
        """Apply crypto-specific sentiment adjustments to the base VADER score."""
        text_lower = text.lower()
        adjustment = 0.0

        for term, boost in self.BULLISH_TERMS.items():
            if term in text_lower:
                adjustment += boost

        for term, penalty in self.BEARISH_TERMS.items():
            if term in text_lower:
                adjustment += penalty  # penalty is already negative

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, base_compound + adjustment))

    def analyze_article(self, title: str, description: str | None = None) -> ArticleSentiment:
        """Analyze sentiment of a single article.

        Parameters
        ----------
        title:
            Article headline.
        description:
            Article body or summary. Can be ``None`` or empty.

        Returns
        -------
        ArticleSentiment with compound score in [-1.0, 1.0].
        """
        description = description or ""
        # Weight title more heavily than description
        combined = f"{title}. {title}. {description}"

        vader_scores = self._vader.polarity_scores(combined)
        compound = self._apply_crypto_adjustment(
            combined, vader_scores["compound"]
        )

        return ArticleSentiment(
            title=title,
            description=description,
            compound_score=round(compound, 4),
            label=self._classify(compound),
            positive_score=round(vader_scores["pos"], 4),
            negative_score=round(vader_scores["neg"], 4),
            neutral_score=round(vader_scores["neu"], 4),
        )

    def analyze_batch(
        self,
        articles: list[dict[str, Any]],
    ) -> BatchSentimentResult:
        """Analyze sentiment for a list of articles and extract keywords.

        Parameters
        ----------
        articles:
            List of dicts, each with at least ``title`` and optionally
            ``description``.

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
            sentiment = self.analyze_article(title, desc)
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

    def extract_keywords(
        self,
        texts: list[str],
        top_n: int = 20,
    ) -> dict[str, float]:
        """Extract top keywords from a corpus using TF-IDF.

        Parameters
        ----------
        texts:
            List of text documents to analyze.
        top_n:
            Number of top keywords to return.

        Returns
        -------
        Dict mapping keyword -> TF-IDF score, sorted by score descending.
        """
        if not texts:
            return {}

        try:
            tfidf_matrix = self._vectorizer.fit_transform(texts)
        except ValueError:
            # All texts empty or only stop words
            self.log.warning("tfidf_fit_failed", reason="empty_corpus")
            return {}

        feature_names = self._vectorizer.get_feature_names_out()
        # Sum TF-IDF scores across all documents for each term
        summed_scores = tfidf_matrix.sum(axis=0).A1  # type: ignore[union-attr]

        # Build sorted dict
        scored = sorted(
            zip(feature_names, summed_scores),
            key=lambda x: x[1],
            reverse=True,
        )

        return {term: float(score) for term, score in scored[:top_n]}
