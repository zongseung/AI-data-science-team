# AI Data Science Team

실시간 크립토 + KRX 주식 데이터 수집/분석 파이프라인

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ BTC 차트  │ │ ETH 차트  │ │ SOL 차트  │ │ HYPE 차트 │  ← WS  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  ┌─────────────────────────────────────────────────┐           │
│  │  NEWS SENTIMENT (TF-IDF + VADER)                │  ← REST  │
│  └─────────────────────────────────────────────────┘           │
│  ┌─────────────────────────────────────────────────┐           │
│  │  OFFICE (에이전트 애니메이션 + 클릭 인터랙션)      │           │
│  └─────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
         │ WebSocket (wss://api.hyperliquid.xyz/ws)
         │ REST (http://localhost:8090/api/sentiment/*)
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Hyperliquid Service (Docker)                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ WS Collector  │  │ News Fetcher │  │  Sentiment   │          │
│  │ BTC/ETH/SOL  │  │ 11 RSS 소스   │  │ TF-IDF+VADER │          │
│  │ 15m봉 실시간  │  │ 비동기 병렬   │  │ 6시간 주기    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┴──────────────────┘                   │
│                           │                                      │
│                    ┌──────▼──────┐                               │
│                    │  Supabase   │                               │
│                    │  (Cloud DB) │                               │
│                    └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Services

| 서비스 | 포트 | 상태 | 역할 |
|--------|------|------|------|
| **hyperliquid-service** | 8090 | **운영중** | WS 캔들 수집 + 뉴스 감성분석 + REST API |
| web-service | 3000 | **운영중** | React 프론트엔드 (차트 + 감성 + 오피스) |
| collection-service | - | 구조완료 | KRX + Hyperliquid 통합 수집 에이전트 |
| analysis-service | - | 구조완료 | 기술분석 + 감성분석 에이전트 |
| forecast-service | - | 구조완료 | 예측 + 백테스트 에이전트 |
| report-service | - | placeholder | 리포트 생성 에이전트 |
| krx-service | 8001 | 코드완료 | KRX 공매도 데이터 |
| api-gateway | 8000 | 코드완료 | FastAPI + WebSocket 게이트웨이 |
| telegram-service | - | placeholder | 텔레그램 봇 |

## Quick Start

### 1. 환경 설정
```bash
cp .env.sample .env
# SUPABASE_URL, SUPABASE_ANON_KEY 입력
```

### 2. Supabase 테이블 생성
SQL Editor에서 실행:
```bash
# 캔들 테이블
cat src/hyperliquid-service/migrations/001_create_tables.sql

# 뉴스 + 감성분석 테이블
cat src/hyperliquid-service/migrations/002_create_news_tables.sql
```

### 3. Docker 실행
```bash
# Hyperliquid collector + sentiment 서비스
docker compose up hyperliquid-collector -d

# 프론트엔드 (dev)
cd src/web-service && npm run dev
```

### 4. 확인
```bash
# Health check
curl http://localhost:8090/health

# 감성분석 수동 실행
curl -X POST http://localhost:8090/api/sentiment/run

# BTC 감성 조회
curl http://localhost:8090/api/sentiment/BTC

# 전체 요약
curl http://localhost:8090/api/sentiment/summary/all
```

## Crypto Data Pipeline

### 실시간 캔들 수집
- **소스**: Hyperliquid WebSocket (`wss://api.hyperliquid.xyz/ws`)
- **코인**: BTC, ETH, SOL, HYPE
- **인터벌**: 15m (설정 변경 가능)
- **저장**: Supabase `hyperliquid_candles` 테이블 (확정 봉만)
- **프론트**: REST snapshot + WS 실시간 업데이트 → Canvas 캔들스틱 차트

### 뉴스 감성분석
- **소스**: 11개 RSS 피드 (비동기 병렬 fetch, API 키 불필요)
  ```
  Tier 1: CoinDesk, CoinTelegraph, TheBlock, CryptoNews, U.Today
  Tier 2: Decrypt, TheDefiant, Blockworks, DailyHodl
  Tier 3: CryptoSlate, AMBCrypto
  ```
- **분석**: scikit-learn TF-IDF 키워드 추출 + NLTK VADER 감성 점수
- **크립토 사전**: bullish/bearish 30개 용어 가중치 보정
- **주기**: 6시간 자동 (startup 시 즉시 1회)
- **저장**: Supabase `crypto_news` + `crypto_sentiment_summary`

### 24h 등락률
- Hyperliquid REST API 1일봉 비교 (전일 종가 vs 현재 종가)
- 상단 마퀴 티커에 KRX 주식과 함께 표시
- 1분마다 자동 갱신

## Frontend

### 3개 탭
| 탭 | 내용 |
|---|---|
| **KRX 주식** | 한국 주식 시세 차트 |
| **CRYPTO** | 2x2 캔들스틱 차트 (BTC/ETH/SOL/HYPE) + NEWS SENTIMENT |
| **OFFICE** | 4팀 22명 에이전트 애니메이션 + 클릭 인터랙션 |

### CRYPTO 탭
- 4분할 실시간 캔들스틱 차트 (1m/5m/15m/1h)
- MA20 이동평균선
- 볼륨바 + 24h 등락률
- 하단: 코인별 뉴스 감성분석 패널 (기사 목록 + 점수 + 키워드)

### OFFICE 탭
- 수집/분석/ML/리포트 4개 팀 방
- 수집팀 캐릭터 클릭 → 실시간 데이터 말풍선
  - 주가수집: BTC/ETH/SOL/HYPE 실시간 가격
  - 뉴스수집: 감성분석 결과 요약
  - 공시수집: RSS 소스별 수집 현황
  - 서무: "수집 완료, 분석팀에게 보낼까요?" 프롬프트
- 방 사이 내부 문으로 에이전트 배달 애니메이션

## Agent System

### BaseAgent (src/shared/agents/)
```python
class BaseAgent(ABC):
    async def execute(**kwargs) -> AgentResult
    # AgentResult: status, data, errors, metadata, timestamp
```

### 구현된 에이전트
| 에이전트 | 위치 | 소스 지원 |
|---|---|---|
| **CollectionAgent** | collection-service/app/agents/ | KRX, Hyperliquid, all |
| **AnalysisAgent** | analysis-service/app/agents/ | KRX, Hyperliquid, all |
| **ForecastAgent** | forecast-service/app/agents/ | KRX, Hyperliquid, all |

### 파이프라인 흐름
```
master_flow(source="all")
  ├─ CollectionAgent → KRX 4개 collector 병렬 + Hyperliquid 캔들
  ├─ AnalysisAgent → 기술분석 + 펀더멘탈 + 감성분석
  ├─ ForecastAgent → 예측 + 백테스트 + 리스크
  └─ ReportAgent → (TODO)
```

## Project Structure

```
.
├── docker-compose.yml              # Hyperliquid collector 서비스
├── .env.sample                     # 환경변수 템플릿
├── docs/
│   └── crypto/                     # 크립토 감성분석 설계 문서
│       ├── README.md               # 아키텍처 + 구현 상태
│       ├── MCP_SETUP.md            # MCP 서버 설정 가이드
│       └── SENTIMENT_SPEC.md       # TF-IDF + VADER 스펙
├── scripts/
│   └── test_hl_ws.py               # WS 연결 테스트
└── src/
    ├── shared/
    │   ├── agents/                  # BaseAgent, AgentResult
    │   ├── config/                  # Settings, Constants, Prefect
    │   ├── nlp/                     # CryptoSentimentAnalyzer
    │   └── utils/                   # EventBus, StorageService
    ├── hyperliquid-service/         # [Docker] 실시간 수집 + 감성분석
    │   ├── app/
    │   │   ├── collector.py         # WS 캔들 수집
    │   │   ├── news_collector.py    # 11개 RSS 병렬 fetch
    │   │   ├── sentiment_task.py    # 6h 주기 감성분석
    │   │   ├── storage.py           # Supabase CRUD
    │   │   ├── config.py            # HyperliquidSettings
    │   │   └── main.py              # FastAPI + lifespan
    │   ├── migrations/              # Supabase SQL
    │   └── Dockerfile
    ├── web-service/                 # React 프론트엔드
    │   └── src/
    │       ├── App.tsx              # 메인 (탭 + 오피스 + 티커)
    │       ├── CryptoChart.tsx      # 4분할 차트 + 감성 패널
    │       ├── StockChart.tsx       # KRX 주식 차트
    │       ├── hooks/
    │       │   └── useHyperliquidWS.ts  # WS + REST 훅
    │       └── types/
    │           └── crypto.ts        # CryptoCandle 타입
    ├── collection-service/          # 수집 에이전트 + Prefect flows
    ├── analysis-service/            # 분석 에이전트
    ├── forecast-service/            # 예측 에이전트
    ├── report-service/              # 리포트 에이전트 (TODO)
    ├── krx-service/                 # KRX 공매도 수집
    ├── api-gateway/                 # FastAPI 게이트웨이
    └── telegram-service/            # 텔레그램 봇 (TODO)
```

## Tech Stack

| 분류 | 기술 |
|---|---|
| **Backend** | Python 3.12, FastAPI, Prefect 3.x, websockets |
| **Frontend** | React 19, TypeScript, Vite, Canvas API |
| **Data** | Supabase (PostgreSQL), Hyperliquid API |
| **ML/NLP** | scikit-learn (TF-IDF), NLTK (VADER), structlog |
| **Infra** | Docker, uvicorn |
| **수집 소스** | Hyperliquid WS, 11개 RSS (CoinDesk, CoinTelegraph 등) |

## API Endpoints (Hyperliquid Service - :8090)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 헬스체크 |
| GET | `/readiness` | collector 상태 |
| GET | `/config` | 현재 설정 |
| GET | `/api/sentiment/{coin}?limit=N` | 코인별 뉴스 + 감성 |
| GET | `/api/sentiment/summary/all` | 전체 코인 감성 요약 |
| POST | `/api/sentiment/run` | 수동 감성분석 트리거 |

## Environment Variables

```bash
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...

# Optional (defaults shown)
HYPERLIQUID_COINS=["BTC","ETH","SOL"]
HYPERLIQUID_INTERVALS=["15m"]
HYPERLIQUID_WS_URL=wss://api.hyperliquid.xyz/ws
```
