# MSA 서비스 구조 (docs 기반)

## 📚 docs 구조 → MSA 서비스 매핑

```
docs/                           src/
├── 02_데이터_수집팀/      →    ├── collection-service/
├── 03_분석팀/            →    ├── analysis-service/
├── 04_전망팀/            →    ├── forecast-service/
├── 04-1_보고서팀/        →    ├── report-service/
├── 05_텔레그램_연동/      →    ├── telegram-service/
├── 06_웹_시각화/         →    ├── web-service/
└── KRX (추가)            →    └── krx-service/
```

---

## 🎯 /src 디렉토리 최종 구조

```
src/
├── README.md                      # MSA 전체 설명
├── docker-compose.yml             # 전체 서비스 오케스트레이션
├── shared/                        # 공통 코드
│   ├── config/                    # 공통 설정
│   │   ├── constants.py          # 종목코드, 섹터
│   │   └── settings.py           # 환경변수
│   └── utils/                     # 공통 유틸리티
│
├── krx-service/                   # Service 1: KRX 데이터 수집
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── api.py                # FastAPI 엔드포인트
│   │   ├── client.py             # KRX HTTP 클라이언트
│   │   └── collector.py          # 수집 로직
│   └── tests/
│
├── collection-service/            # Service 2: 데이터 수집 (네이버/DART)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── api.py
│   │   ├── collectors/
│   │   │   ├── stock_price.py    # 네이버 금융
│   │   │   ├── disclosure.py     # DART
│   │   │   ├── news.py           # 뉴스
│   │   │   └── market.py         # 시장 데이터
│   │   └── flows/
│   └── tests/
│
├── analysis-service/              # Service 3: 분석팀 (EDA/피처/통계)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── api.py
│   │   ├── agents/
│   │   │   ├── eda_agent.py
│   │   │   ├── feature_agent.py
│   │   │   ├── statistical_agent.py
│   │   │   ├── sentiment_agent.py
│   │   │   └── sector_agent.py
│   │   └── flows/
│   └── tests/
│
├── forecast-service/              # Service 4: 전망팀 (ML/백테스트)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── api.py
│   │   ├── agents/
│   │   │   ├── model_training_agent.py
│   │   │   ├── backtest_agent.py
│   │   │   └── risk_agent.py
│   │   ├── models/               # ML 모델
│   │   └── flows/
│   └── tests/
│
├── report-service/                # Service 5: 보고서팀
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── api.py
│   │   ├── agents/
│   │   │   ├── comprehensive_reporter.py
│   │   │   ├── investment_memo_writer.py
│   │   │   ├── risk_note_writer.py
│   │   │   └── editor.py
│   │   └── flows/
│   └── tests/
│
├── telegram-service/              # Service 6: 텔레그램 봇
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── bot.py                # 봇 메인
│   │   ├── handlers/             # 명령어 핸들러
│   │   └── formatters/           # 메시지 포맷터
│   └── tests/
│
├── web-service/                   # Service 7: 웹 시각화 (React + PixiJS)
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pixi/                 # PixiJS 애니메이션
│   │   └── api/                  # API 클라이언트
│   └── public/
│
└── api-gateway/                   # Service 8: API Gateway (Nginx)
    ├── Dockerfile
    ├── nginx.conf
    └── certs/
```

---

## 🔄 서비스 간 통신 흐름

```
[사용자]
   ↓
[api-gateway :80]
   ├─→ [web-service :3000]         React + PixiJS UI
   ├─→ [telegram-service :8006]    봇 webhook
   │
   ├─→ [collection-service :8002]  데이터 수집 오케스트레이션
   │      ├─→ [krx-service :8001]      KRX 공매도
   │      ├─→ Naver Finance (외부)
   │      └─→ DART API (외부)
   │
   ├─→ [analysis-service :8003]    분석 (EDA/피처/통계)
   ├─→ [forecast-service :8004]    예측 (ML/백테스트)
   └─→ [report-service :8005]      보고서 생성
```

---

## 🗄️ 공통 인프라

```yaml
# docker-compose.yml 일부
services:
  # Database
  postgres:
    image: supabase/postgres:15
    ports: ["5432:5432"]

  # Cache
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  # Message Queue (향후)
  rabbitmq:
    image: rabbitmq:3-management
    ports: ["5672:5672", "15672:15672"]

  # Prefect Server (오케스트레이션)
  prefect-server:
    image: prefecthq/prefect:2-python3.12
    ports: ["4200:4200"]
```

---

## 📦 각 서비스별 역할

### 1. krx-service (Port 8001)
**역할**: KRX 공매도 데이터 수집 전담
- API: `POST /api/v1/collect`
- 기술: FastAPI + httpx + pandas
- 의존성: 없음 (독립)

### 2. collection-service (Port 8002)
**역할**: 전체 데이터 수집 오케스트레이션
- API: `POST /api/v1/collect/{stock_name}`
- 기술: Prefect + Playwright + httpx
- 의존성: krx-service

### 3. analysis-service (Port 8003)
**역할**: 데이터 분석 (EDA, 피처, 통계, 감성, 섹터)
- API: `POST /api/v1/analyze`
- 기술: Pandas + NumPy + scikit-learn + LLM
- 의존성: collection-service

### 4. forecast-service (Port 8004)
**역할**: ML 모델 학습 + 백테스트 + 리스크
- API: `POST /api/v1/forecast`
- 기술: XGBoost + LightGBM + Prophet + LSTM + MLflow
- 의존성: analysis-service

### 5. report-service (Port 8005)
**역할**: 보고서 생성 (종합/투자메모/리스크노트)
- API: `POST /api/v1/report`
- 기술: LLM (GPT-4/Claude)
- 의존성: analysis-service + forecast-service

### 6. telegram-service (Port 8006)
**역할**: 텔레그램 봇 인터페이스
- API: Webhook `/webhook`
- 기술: python-telegram-bot
- 의존성: 모든 서비스 (오케스트레이션)

### 7. web-service (Port 3000)
**역할**: 웹 UI (PixiJS 애니메이션)
- 기술: React 19 + PixiJS 8 + TypeScript
- 의존성: api-gateway (WebSocket)

### 8. api-gateway (Port 80)
**역할**: 라우팅 + 로드밸런싱
- 기술: Nginx
- 의존성: 모든 서비스

---

## 🚀 다음 작업 순서

### Step 1: 디렉토리 구조 생성
```bash
mkdir -p src/{shared/{config,utils},krx-service,collection-service,analysis-service,forecast-service,report-service,telegram-service,web-service,api-gateway}
```

### Step 2: 기존 코드 이동
- `/src/krx/` → `/src/krx-service/app/`
- `/ai_data_science_team/collectors/` → `/src/collection-service/app/collectors/`
- `/ai_data_science_team/config/` → `/src/shared/config/`

### Step 3: 각 서비스별 Dockerfile + requirements.txt 작성

### Step 4: docker-compose.yml 작성

---

## 📝 현재 상태

✅ **완료**:
- KRX 수집 로직 (현재 `/src/krx`)
- Collection 로직 (현재 `/ai_data_science_team/collectors`)
- Flows 기본 구조 (현재 `/ai_data_science_team/flows`)

⬜ **예정**:
- MSA 폴더 구조로 재구성
- 각 서비스별 Dockerfile
- docker-compose.yml
- API Gateway 설정

시작하시겠습니까?
