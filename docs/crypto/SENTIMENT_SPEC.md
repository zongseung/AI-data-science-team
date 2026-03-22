# TF-IDF + VADER Sentiment Analysis Specification

암호화폐 뉴스 기사에 대한 감성 분석 엔진의 상세 기술 스펙입니다. TF-IDF로 키워드를 추출하고, VADER로 감성 점수를 산출한 뒤, 암호화폐 도메인 특화 lexicon으로 보정합니다.

---

## Input Format

### Per-Article Input

```python
@dataclass
class ArticleInput:
    title: str          # 기사 제목 (필수)
    description: str    # 기사 요약/본문 (선택, 없으면 title만 사용)
    coin: str           # 코인 심볼 (BTC, ETH, SOL, HYPE)
    source: str         # 출처 (coindesk, cointelegraph, etc.)
    url: str            # 원문 URL
    published_at: str   # ISO 8601 형식 발행 시간
```

### 텍스트 전처리

분석 전 다음 전처리를 수행합니다:

1. **결합**: `title + " " + description`을 하나의 텍스트로 결합
2. **소문자 변환**: 전체 텍스트를 lowercase로 변환
3. **URL 제거**: `http(s)://...` 패턴 제거
4. **HTML 태그 제거**: `<tag>` 패턴 제거
5. **특수문자 정리**: 분석에 불필요한 특수문자 제거 (단, `$`, `%`, `#` 등 금융 관련 기호는 유지)
6. **공백 정규화**: 연속 공백을 단일 공백으로

```python
import re

def preprocess_text(title: str, description: str = "") -> str:
    text = f"{title} {description}".strip()
    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s$%#@.,-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
```

---

## TF-IDF Keyword Extraction

### Parameters

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(
    max_features=1000,       # 최대 feature 수
    ngram_range=(1, 2),      # unigram + bigram
    stop_words="english",    # 영어 불용어 제거
    min_df=1,                # 최소 문서 빈도 (단일 기사도 포함)
    max_df=0.95,             # 95% 이상 문서에 등장하는 단어 제거
    sublinear_tf=True,       # TF에 로그 스케일링 적용 (1 + log(tf))
    dtype=float,
)
```

### 파라미터 상세 설명

| Parameter | Value | 근거 |
|-----------|-------|------|
| `max_features` | 1000 | 뉴스 기사의 어휘 다양성 고려, 메모리 효율성 |
| `ngram_range` | (1, 2) | "bitcoin price"같은 bigram 패턴 포착 |
| `stop_words` | "english" | 일반 영어 불용어 제거 |
| `min_df` | 1 | 배치 크기가 작을 수 있으므로 1로 설정 |
| `max_df` | 0.95 | 거의 모든 기사에 등장하는 일반적 단어 제거 |
| `sublinear_tf` | True | 빈도가 높은 단어의 과도한 가중치 방지 |

### 키워드 추출 방법

```python
def extract_keywords(text: str, vectorizer: TfidfVectorizer, top_n: int = 10) -> list[dict]:
    """단일 기사에서 TF-IDF 기반 상위 키워드 추출"""
    tfidf_matrix = vectorizer.fit_transform([text])
    feature_names = vectorizer.get_feature_names_out()
    scores = tfidf_matrix.toarray()[0]

    # 상위 N개 키워드 추출
    top_indices = scores.argsort()[-top_n:][::-1]
    keywords = [
        {"keyword": feature_names[i], "score": round(float(scores[i]), 4)}
        for i in top_indices
        if scores[i] > 0
    ]
    return keywords
```

### 배치 처리 시 TF-IDF

여러 기사를 한 번에 처리할 때는 전체 corpus에 대해 fit하고, 개별 기사의 벡터에서 키워드를 추출합니다:

```python
def extract_keywords_batch(
    texts: list[str],
    vectorizer: TfidfVectorizer,
    top_n: int = 10,
) -> list[list[dict]]:
    """배치 기사에서 TF-IDF 키워드 추출"""
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    all_keywords = []
    for i in range(len(texts)):
        scores = tfidf_matrix[i].toarray()[0]
        top_indices = scores.argsort()[-top_n:][::-1]
        keywords = [
            {"keyword": feature_names[j], "score": round(float(scores[j]), 4)}
            for j in top_indices
            if scores[j] > 0
        ]
        all_keywords.append(keywords)

    return all_keywords
```

---

## VADER Sentiment Scoring

### 개요

VADER (Valence Aware Dictionary and sEntiment Reasoner)는 소셜 미디어와 뉴스 텍스트에 특화된 rule-based 감성 분석 도구입니다.

### 설치 및 초기화

```python
import nltk
nltk.download("vader_lexicon")

from nltk.sentiment.vader import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()
```

### Scoring Method

```python
def score_sentiment_vader(text: str) -> dict:
    """VADER로 텍스트 감성 점수 산출"""
    scores = analyzer.polarity_scores(text)
    return {
        "positive": scores["pos"],   # 긍정 비율 (0.0 ~ 1.0)
        "negative": scores["neg"],   # 부정 비율 (0.0 ~ 1.0)
        "neutral": scores["neu"],    # 중립 비율 (0.0 ~ 1.0)
        "compound": scores["compound"],  # 종합 점수 (-1.0 ~ 1.0)
    }
```

### VADER Compound Score 해석

| Compound Score | 해석 |
|----------------|------|
| >= 0.05 | Positive |
| <= -0.05 | Negative |
| -0.05 < score < 0.05 | Neutral |

- Compound score는 모든 어휘 점수를 정규화한 값
- -1.0 (가장 부정적) ~ +1.0 (가장 긍정적)
- 0에 가까울수록 중립적

---

## Crypto-Specific Keyword Adjustments

VADER는 일반 영어 텍스트에 최적화되어 있으므로, 암호화폐 도메인에서 자주 사용되는 특수 표현에 대한 보정이 필요합니다.

### Bullish Keywords (긍정 보정)

점수 보정: **+0.1 per keyword match**

```python
BULLISH_KEYWORDS = {
    # 강한 긍정 (+0.15)
    "strong_bullish": [
        "moon", "mooning", "to the moon",
        "breakout", "broke out",
        "all time high", "ath", "new ath",
        "parabolic",
        "massive rally",
        "institutional adoption",
    ],
    # 일반 긍정 (+0.1)
    "bullish": [
        "bullish", "bull run", "bull market",
        "pump", "pumping",
        "rally", "rallied", "rallying",
        "surge", "surged", "surging",
        "soar", "soared", "soaring",
        "breakout", "breaking out",
        "adoption", "mass adoption",
        "accumulation", "accumulating",
        "buy signal", "buy the dip", "btd",
        "whale buying", "whale accumulation",
        "green candle", "green day",
        "higher high", "higher low",
        "golden cross",
        "support held", "bounced",
        "inflow", "inflows",
        "etf approval", "etf approved",
        "halving",
    ],
    # 약한 긍정 (+0.05)
    "mild_bullish": [
        "recovery", "recovering",
        "rebound", "rebounded",
        "stabilized", "stabilizing",
        "holding support",
        "consolidation above",
        "upgrade", "upgraded",
        "partnership", "partnered",
        "launch", "launched",
        "integration",
    ],
}
```

### Bearish Keywords (부정 보정)

점수 보정: **-0.1 per keyword match**

```python
BEARISH_KEYWORDS = {
    # 강한 부정 (-0.15)
    "strong_bearish": [
        "crash", "crashed", "crashing",
        "rug pull", "rugged",
        "scam", "fraud", "ponzi",
        "hack", "hacked", "exploit",
        "bankrupt", "bankruptcy", "insolvent",
        "death cross",
        "capitulation",
        "black swan",
    ],
    # 일반 부정 (-0.1)
    "bearish": [
        "bearish", "bear market",
        "dump", "dumped", "dumping",
        "crash", "crashed",
        "plunge", "plunged", "plunging",
        "tank", "tanked", "tanking",
        "sell-off", "selloff", "selling pressure",
        "fud", "fear uncertainty doubt",
        "liquidation", "liquidated",
        "red candle", "red day", "blood red",
        "lower low", "lower high",
        "resistance rejected",
        "outflow", "outflows",
        "whale selling", "whale dump",
        "delisted", "delisting",
        "sec lawsuit", "regulatory crackdown",
        "ban", "banned",
    ],
    # 약한 부정 (-0.05)
    "mild_bearish": [
        "correction", "correcting",
        "pullback", "pull back",
        "dip", "dipped", "dipping",
        "decline", "declined", "declining",
        "weakness", "weakening",
        "uncertainty",
        "concern", "concerns",
        "warning", "cautious",
        "overbought",
        "resistance",
        "regulation", "regulatory",
    ],
}
```

### 보정 로직

```python
def apply_crypto_adjustment(text: str, base_score: float) -> tuple[float, str]:
    """
    Crypto-specific 키워드 보정 적용

    Args:
        text: 전처리된 텍스트 (lowercase)
        base_score: VADER compound score

    Returns:
        (adjusted_score, sentiment_label)
    """
    adjustment = 0.0
    text_lower = text.lower()

    # Bullish 키워드 체크
    for keyword in BULLISH_KEYWORDS["strong_bullish"]:
        if keyword in text_lower:
            adjustment += 0.15

    for keyword in BULLISH_KEYWORDS["bullish"]:
        if keyword in text_lower:
            adjustment += 0.10

    for keyword in BULLISH_KEYWORDS["mild_bullish"]:
        if keyword in text_lower:
            adjustment += 0.05

    # Bearish 키워드 체크
    for keyword in BEARISH_KEYWORDS["strong_bearish"]:
        if keyword in text_lower:
            adjustment -= 0.15

    for keyword in BEARISH_KEYWORDS["bearish"]:
        if keyword in text_lower:
            adjustment -= 0.10

    for keyword in BEARISH_KEYWORDS["mild_bearish"]:
        if keyword in text_lower:
            adjustment -= 0.05

    # 보정 상한/하한 (-0.3 ~ +0.3)
    adjustment = max(-0.3, min(0.3, adjustment))

    # 최종 점수 계산
    final_score = base_score + adjustment
    final_score = max(-1.0, min(1.0, final_score))  # Clamp to [-1.0, 1.0]

    # Label 결정
    if final_score > 0.05:
        label = "positive"
    elif final_score < -0.05:
        label = "negative"
    else:
        label = "neutral"

    return round(final_score, 4), label
```

---

## Output Format

### Per-Article Output

```python
@dataclass
class ArticleSentiment:
    coin: str                    # "BTC"
    title: str                   # 원본 제목
    description: str             # 원본 설명
    source: str                  # "coindesk"
    url: str                     # 원문 URL
    published_at: str            # ISO 8601
    sentiment_score: float       # -1.0 ~ 1.0 (보정 후 최종 점수)
    sentiment_label: str         # "positive" | "neutral" | "negative"
    vader_compound: float        # VADER 원본 compound score
    crypto_adjustment: float     # 도메인 보정값
    keywords: list[dict]         # [{"keyword": "bitcoin rally", "score": 0.4523}, ...]
```

JSON 출력 예시:

```json
{
    "coin": "BTC",
    "title": "Bitcoin Surges Past $100K as ETF Inflows Hit Record",
    "description": "Institutional demand drives bitcoin to new all-time high...",
    "source": "coindesk",
    "url": "https://coindesk.com/...",
    "published_at": "2026-03-22T10:30:00Z",
    "sentiment_score": 0.8742,
    "sentiment_label": "positive",
    "vader_compound": 0.6742,
    "crypto_adjustment": 0.2,
    "keywords": [
        {"keyword": "bitcoin", "score": 0.5231},
        {"keyword": "etf inflows", "score": 0.4102},
        {"keyword": "all time high", "score": 0.3856},
        {"keyword": "institutional", "score": 0.3214},
        {"keyword": "surges", "score": 0.2987}
    ]
}
```

### Aggregate Output (코인별 집계)

```python
@dataclass
class CoinSentimentSummary:
    coin: str                    # "BTC"
    period_start: str            # ISO 8601
    period_end: str              # ISO 8601
    avg_sentiment: float         # 평균 감성 점수
    sentiment_label: str         # 종합 레이블
    article_count: int           # 분석된 기사 수
    positive_count: int          # 긍정 기사 수
    negative_count: int          # 부정 기사 수
    neutral_count: int           # 중립 기사 수
    top_keywords: list[dict]     # 전체 기사 통합 상위 키워드
```

JSON 출력 예시:

```json
{
    "coin": "BTC",
    "period_start": "2026-03-22T00:00:00Z",
    "period_end": "2026-03-22T06:00:00Z",
    "avg_sentiment": 0.3521,
    "sentiment_label": "positive",
    "article_count": 24,
    "positive_count": 15,
    "negative_count": 4,
    "neutral_count": 5,
    "top_keywords": [
        {"keyword": "bitcoin", "score": 0.612},
        {"keyword": "etf", "score": 0.389},
        {"keyword": "price", "score": 0.312}
    ]
}
```

---

## Example Calculation Walkthrough

실제 기사를 예시로 전체 분석 과정을 단계별로 설명합니다.

### 입력 기사

```
Title: "Bitcoin Surges Past $100K as Institutional Adoption Grows, ETF Inflows Hit Record"
Description: "Bitcoin reached a new all-time high today, surging past the $100,000 mark
             as institutional investors pour into spot Bitcoin ETFs. Whale accumulation
             has been at its highest level since 2024."
Coin: BTC
```

### Step 1: 텍스트 전처리

```
Input:  "Bitcoin Surges Past $100K as Institutional Adoption Grows, ETF Inflows Hit Record
         Bitcoin reached a new all-time high today, surging past the $100,000 mark
         as institutional investors pour into spot Bitcoin ETFs. Whale accumulation
         has been at its highest level since 2024."

Output: "bitcoin surges past $100k as institutional adoption grows, etf inflows hit record
         bitcoin reached a new all-time high today, surging past the $100,000 mark
         as institutional investors pour into spot bitcoin etfs. whale accumulation
         has been at its highest level since 2024."
```

### Step 2: TF-IDF Keyword Extraction

```python
keywords = extract_keywords(preprocessed_text, vectorizer, top_n=5)
# Result:
# [
#     {"keyword": "bitcoin", "score": 0.5231},
#     {"keyword": "institutional", "score": 0.4102},
#     {"keyword": "etf inflows", "score": 0.3856},
#     {"keyword": "all time high", "score": 0.3214},
#     {"keyword": "whale accumulation", "score": 0.2987},
# ]
```

### Step 3: VADER Scoring

```python
scores = analyzer.polarity_scores(preprocessed_text)
# Result:
# {
#     "pos": 0.15,
#     "neg": 0.0,
#     "neu": 0.85,
#     "compound": 0.6742
# }

base_score = 0.6742  # 전반적으로 긍정적
```

### Step 4: Crypto Keyword Adjustment

텍스트에서 발견된 crypto-specific 키워드:

| Keyword | Category | Adjustment |
|---------|----------|------------|
| "all time high" | strong_bullish | +0.15 |
| "surges" / "surging" | bullish | +0.10 |
| "adoption" | bullish | +0.10 |
| "whale accumulation" | bullish | +0.10 |
| "inflows" | bullish | +0.10 |

```
Total adjustment = +0.15 + 0.10 + 0.10 + 0.10 + 0.10 = +0.55
Capped adjustment = +0.30  (상한 적용)
```

### Step 5: 최종 점수 계산

```
final_score = base_score + capped_adjustment
            = 0.6742 + 0.30
            = 0.9742

Clamped to [-1.0, 1.0] → 0.9742

Label: "positive" (> 0.05)
```

### Step 6: 최종 출력

```json
{
    "coin": "BTC",
    "title": "Bitcoin Surges Past $100K as Institutional Adoption Grows, ETF Inflows Hit Record",
    "sentiment_score": 0.9742,
    "sentiment_label": "positive",
    "vader_compound": 0.6742,
    "crypto_adjustment": 0.30,
    "keywords": [
        {"keyword": "bitcoin", "score": 0.5231},
        {"keyword": "institutional", "score": 0.4102},
        {"keyword": "etf inflows", "score": 0.3856},
        {"keyword": "all time high", "score": 0.3214},
        {"keyword": "whale accumulation", "score": 0.2987}
    ]
}
```

---

## Performance Considerations

### 처리 속도

| Component | 예상 처리 시간 | 비고 |
|-----------|---------------|------|
| 텍스트 전처리 | ~1ms / article | Regex 기반, 매우 빠름 |
| TF-IDF fit_transform | ~50ms / 100 articles | 배치 처리 시 |
| VADER scoring | ~5ms / article | 단일 텍스트 기준 |
| Crypto adjustment | ~1ms / article | Dictionary lookup |
| **전체 파이프라인** | **~100ms / 100 articles** | 배치 기준 |

### 메모리 사용량

- TF-IDF vectorizer (`max_features=1000`): ~10MB
- VADER lexicon: ~5MB
- 100개 기사 처리 시 전체 메모리: ~50MB

### 최적화 전략

1. **배치 처리**: 개별 기사가 아닌 배치 단위로 TF-IDF fit 수행
2. **Vectorizer 캐싱**: 한번 fit된 vectorizer를 재사용 (동일 수집 주기 내)
3. **Lazy Loading**: VADER lexicon은 최초 호출 시 한 번만 로드
4. **비동기 처리**: 수집과 분석을 async로 병렬 수행

### 제약 사항

- **언어**: 영문 기사에 최적화 (한글 기사는 별도 처리 필요)
- **컨텍스트**: 기사 단위 분석이므로 문맥 간 관계는 파악하지 않음
- **풍자/반어**: VADER는 rule-based이므로 풍자 표현 탐지 불가
- **시장 상황**: 동일 키워드도 시장 상황에 따라 의미가 다를 수 있음 (예: "correction"이 과열 시장에서는 긍정적일 수 있음)

### 향후 개선 방안

1. **FinBERT 도입**: 금융 도메인 특화 BERT 모델로 accuracy 향상
2. **한글 지원**: KoBERT 또는 한국어 VADER lexicon 추가
3. **시계열 감성**: 감성 점수의 시간적 변화 추적 및 trend 감지
4. **Cross-article 분석**: 동일 이벤트에 대한 여러 기사 종합 분석

---

## Dependencies

```toml
# pyproject.toml에 추가 필요
[project.dependencies]
scikit-learn = ">=1.3.0"   # TF-IDF (이미 포함)
nltk = ">=3.8.0"           # VADER sentiment (추가 필요)

# 초기 setup 시 VADER lexicon 다운로드 필요
# python -c "import nltk; nltk.download('vader_lexicon')"
```

### NLTK Data 자동 다운로드

```python
import nltk
import os

def ensure_vader_lexicon():
    """VADER lexicon이 없으면 자동 다운로드"""
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
```
