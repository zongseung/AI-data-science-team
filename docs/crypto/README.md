# Crypto News Sentiment Analysis System

암호화폐 뉴스를 자동 수집하고, TF-IDF + VADER 기반 감성 분석을 수행하여 코인별 시장 심리를 실시간으로 파악하는 시스템입니다.

---

## Architecture

```
[News Sources] → [Collector (6hr cron)] → [Supabase storage] → [TF-IDF + VADER Analysis] → [Frontend display]
```

전체 파이프라인은 6시간 주기로 실행되며, 뉴스 수집부터 감성 분석, 저장, 프론트엔드 표시까지 자동화되어 있습니다.

```
┌─────────────────────┐
│   News Sources      │
│  - Free Crypto API  │
│  - RSS Feeds        │
│  - CryptoPanic      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Collector (6hr)    │
│  - MCP integration  │
│  - HTTP fallback    │
│  - Rate limiting    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Supabase Storage   │
│  - crypto_news      │
│  - sentiment_summary│
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Sentiment Analysis │
│  - TF-IDF keywords  │
│  - VADER scoring    │
│  - Crypto lexicon   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Frontend Display   │
│  - Sentiment bar    │
│  - Article list     │
│  - Per-coin chart   │
└─────────────────────┘
```

---

## News Sources (MCP 자동 수집)

### Primary: Free Crypto News API

- **URL**: https://github.com/nirholas/free-crypto-news
- **인증**: API key 불필요 (완전 무료)
- **MCP**: Claude MCP integration용 공식 서버 제공
- **데이터 규모**: 660,000+ article archive
- **지원 필터**: BTC, ETH, SOL, HYPE
- **장점**: 가장 포괄적인 무료 암호화폐 뉴스 소스, MCP 직접 연동 가능

### Backup: RSS Feeds

MCP 서버 장애 또는 API 접근 불가 시 RSS feed로 fallback합니다.

| Source | RSS URL | 인증 | 상태 |
|--------|---------|------|------|
| CoinDesk | https://www.coindesk.com/arc/outboundfeeds/rss/ | 불필요 | 확인됨 (2026-03-22) |
| CoinTelegraph | https://cointelegraph.com/rss | 불필요 | 확인됨 (2026-03-22) |

- 두 소스 모두 무료이며 인증 없이 접근 가능
- RSS XML 파싱으로 title, description, link, pubDate 추출
- 코인별 필터링은 title/description 내 키워드 매칭으로 수행

---

## MCP Integration

이 시스템은 Claude MCP(Model Context Protocol)를 통해 뉴스 데이터를 수집합니다.

### 사용 가능한 MCP Server 목록

| MCP Server | 용도 | 인증 |
|------------|------|------|
| Free Crypto News API | 메인 뉴스 수집 | 불필요 |
| RSS Reader MCP ([kwp-lab/rss-reader-mcp](https://github.com/kwp-lab/rss-reader-mcp)) | RSS feed 수집 | 불필요 |
| CryptoPanic MCP Server | 소셜 감성 데이터 | 무료 토큰 필요 |

### 설정 방법

`.claude/settings.local.json`에 MCP 서버를 등록합니다. 상세 설정은 [MCP_SETUP.md](./MCP_SETUP.md)를 참조하세요.

### Fallback 전략

MCP 서버 접근 불가 시 direct HTTP 요청으로 자동 전환됩니다:
1. MCP server 호출 시도
2. 3회 재시도 후 실패 시 HTTP fallback 활성화
3. HTTP fallback도 실패 시 이전 수집 데이터 유지 + alert 발송

---

## Sentiment Analysis Pipeline

감성 분석은 TF-IDF keyword extraction과 VADER sentiment scoring을 조합하여 수행합니다. 상세 스펙은 [SENTIMENT_SPEC.md](./SENTIMENT_SPEC.md)를 참조하세요.

### 분석 방법 요약

1. **TF-IDF Keyword Extraction**: scikit-learn `TfidfVectorizer`로 기사별 핵심 키워드 추출 (이미 의존성에 포함)
2. **VADER Sentiment Scoring**: NLTK VADER로 문장 단위 감성 점수 산출 (의존성 추가 필요)
3. **Crypto-specific Lexicon Boost**: 암호화폐 도메인 특화 키워드로 점수 보정
   - Bullish 키워드: `bullish`, `moon`, `pump`, `breakout`, `rally`, `ATH`, `adoption` 등
   - Bearish 키워드: `bearish`, `dump`, `crash`, `FUD`, `rug pull`, `liquidation` 등

### Output Format

- **Per-article**: sentiment score (-1.0 ~ +1.0) + sentiment label (positive/neutral/negative) + keywords
- **Aggregate**: 코인별 평균 감성 점수 + 기사 수 + positive/negative/neutral 비율

---

## Data Flow

전체 데이터 흐름을 단계별로 설명합니다.

### Step 1: 뉴스 수집 (Every 6 hours)

```python
# Cron schedule: 0 */6 * * *
# MCP 또는 HTTP를 통해 최신 기사 수집
articles = await collector.fetch_latest(coins=["BTC", "ETH", "SOL", "HYPE"])
```

- 6시간 주기 cron으로 실행 (00:00, 06:00, 12:00, 18:00 UTC)
- 중복 기사는 URL 기반으로 필터링
- Rate limiting 적용 (분당 요청 수 제한)

### Step 2: 코인별 필터링

```python
# Title + description에서 코인 키워드 매칭
coin_keywords = {
    "BTC": ["bitcoin", "btc", "비트코인"],
    "ETH": ["ethereum", "eth", "이더리움"],
    "SOL": ["solana", "sol", "솔라나"],
    "HYPE": ["hyperliquid", "hype", "하이퍼리퀴드"],
}
```

- 하나의 기사가 여러 코인에 매칭될 수 있음
- 대소문자 구분 없이 매칭
- 한글 키워드도 지원

### Step 3: TF-IDF Vectorization

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
tfidf_matrix = vectorizer.fit_transform(texts)  # title + description
```

- Title과 description을 결합하여 TF-IDF 벡터 생성
- 기사별 상위 키워드 추출하여 저장

### Step 4: VADER Sentiment Scoring

```python
from nltk.sentiment.vader import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()
scores = analyzer.polarity_scores(text)
compound_score = scores["compound"]  # -1.0 to 1.0
```

- VADER compound score를 기본 감성 점수로 사용
- 영문 텍스트에 최적화되어 있음

### Step 5: Crypto Keyword Adjustment

```python
# Crypto-specific 키워드가 포함된 경우 점수 보정
adjusted_score = compound_score + crypto_adjustment
adjusted_score = max(-1.0, min(1.0, adjusted_score))  # Clamp to [-1.0, 1.0]
```

- Bullish 키워드 발견 시 +0.1 보정
- Bearish 키워드 발견 시 -0.1 보정
- 최종 점수는 -1.0 ~ 1.0 범위로 clamping

### Step 6: Supabase 저장

```python
# 기사별 결과 저장
await supabase.table("crypto_news").upsert(article_with_sentiment)

# 코인별 집계 결과 저장
await supabase.table("crypto_sentiment_summary").upsert(aggregated_sentiment)
```

- `crypto_news` 테이블에 기사별 감성 분석 결과 저장
- `crypto_sentiment_summary` 테이블에 기간별 집계 결과 저장
- Upsert로 중복 방지

### Step 7: Frontend Display

- 각 코인 차트 하단에 sentiment bar 표시
- 최근 기사 목록을 감성 점수와 함께 표시
- 색상 코딩: 양수(초록), 중립(회색), 음수(빨강)

---

## Supabase Tables

### `crypto_news` - 기사별 감성 분석 결과

```sql
CREATE TABLE crypto_news (
    id BIGSERIAL PRIMARY KEY,
    coin TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT,
    url TEXT,
    published_at TIMESTAMPTZ,
    sentiment_score NUMERIC,  -- -1.0 to 1.0
    sentiment_label TEXT,     -- positive/neutral/negative
    keywords JSONB,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- 검색 성능을 위한 인덱스
CREATE INDEX idx_crypto_news_coin ON crypto_news(coin);
CREATE INDEX idx_crypto_news_published_at ON crypto_news(published_at DESC);
CREATE INDEX idx_crypto_news_coin_published ON crypto_news(coin, published_at DESC);
CREATE UNIQUE INDEX idx_crypto_news_url ON crypto_news(url);
```

| Column | Type | 설명 |
|--------|------|------|
| `id` | BIGSERIAL | Primary key |
| `coin` | TEXT | 코인 심볼 (BTC, ETH, SOL, HYPE) |
| `title` | TEXT | 기사 제목 |
| `description` | TEXT | 기사 요약/본문 |
| `source` | TEXT | 출처 (coindesk, cointelegraph, etc.) |
| `url` | TEXT | 원문 URL (중복 체크용) |
| `published_at` | TIMESTAMPTZ | 기사 발행 시간 |
| `sentiment_score` | NUMERIC | 감성 점수 (-1.0 ~ 1.0) |
| `sentiment_label` | TEXT | 감성 레이블 (positive/neutral/negative) |
| `keywords` | JSONB | TF-IDF 추출 키워드 목록 |
| `collected_at` | TIMESTAMPTZ | 수집 시간 |

### `crypto_sentiment_summary` - 기간별 집계 결과

```sql
CREATE TABLE crypto_sentiment_summary (
    id BIGSERIAL PRIMARY KEY,
    coin TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    avg_sentiment NUMERIC,
    sentiment_label TEXT,
    article_count INT,
    top_keywords JSONB,
    positive_count INT,
    negative_count INT,
    neutral_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(coin, period_start)
);

-- 검색 성능을 위한 인덱스
CREATE INDEX idx_sentiment_summary_coin ON crypto_sentiment_summary(coin);
CREATE INDEX idx_sentiment_summary_period ON crypto_sentiment_summary(period_start DESC);
```

| Column | Type | 설명 |
|--------|------|------|
| `id` | BIGSERIAL | Primary key |
| `coin` | TEXT | 코인 심볼 |
| `period_start` | TIMESTAMPTZ | 집계 시작 시간 |
| `period_end` | TIMESTAMPTZ | 집계 종료 시간 |
| `avg_sentiment` | NUMERIC | 평균 감성 점수 |
| `sentiment_label` | TEXT | 종합 감성 레이블 |
| `article_count` | INT | 분석된 기사 수 |
| `top_keywords` | JSONB | 상위 키워드 목록 |
| `positive_count` | INT | 긍정 기사 수 |
| `negative_count` | INT | 부정 기사 수 |
| `neutral_count` | INT | 중립 기사 수 |
| `created_at` | TIMESTAMPTZ | 레코드 생성 시간 |

### Sentiment Label 기준

| Score Range | Label |
|-------------|-------|
| score > 0.05 | `positive` |
| score < -0.05 | `negative` |
| -0.05 <= score <= 0.05 | `neutral` |

---

## Implementation Status

- [x] API research completed - 무료 뉴스 소스 조사 완료
- [x] Architecture design - 전체 파이프라인 설계 완료
- [x] Feasibility confirmed - 기술적 타당성 확인 (API 접근, 라이브러리 호환성)
- [ ] News collector implementation - MCP/HTTP 뉴스 수집기 구현
- [ ] TF-IDF + VADER sentiment scorer - 감성 분석 엔진 구현
- [ ] Supabase tables - 테이블 생성 및 마이그레이션
- [ ] Frontend display - 감성 바 + 기사 목록 UI
- [ ] MCP server configuration - `.claude/settings.local.json` 설정
- [ ] 6-hour cron schedule - Prefect 스케줄 등록

---

## 관련 문서

- [MCP Server 설정 가이드](./MCP_SETUP.md)
- [TF-IDF + VADER 감성 분석 상세 스펙](./SENTIMENT_SPEC.md)

## Dependencies

### 이미 포함된 의존성
- `scikit-learn` - TF-IDF vectorization
- `httpx` - HTTP fallback 요청
- `supabase` - 데이터 저장

### 추가 필요한 의존성
- `nltk` - VADER sentiment analysis
- `feedparser` - RSS feed 파싱 (backup source용)
