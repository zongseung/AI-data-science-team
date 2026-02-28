# AI Financial Data Science Team - PRD (Product Requirements Document)

## 1. 프로젝트 개요

### 1.1 프로젝트명
**AI Financial Data Science Team** (AI 금융 데이터 사이언스 팀)

### 1.2 비전
AI 에이전트들이 각 팀(수집, 분석, 전망)으로 구성되어 **데이터 사이언스 방법론**(EDA, 피처 엔지니어링, ML/DL 모델링, 백테스팅)을 적용하여 한국 주식시장 데이터를 수집-분석-예측하고, 그 과정을 웹에서 캐릭터 애니메이션으로 시각화하며, 결과를 텔레그램으로 전달하는 시스템

### 1.3 벤치마크
- **Claw-Empire** (https://github.com/GreenSheep01201/claw-empire)
  - PixiJS 기반 픽셀아트 오피스 시뮬레이터
  - 다중 AI 에이전트 오케스트레이션
  - 실시간 WebSocket 통신
  - 팀/부서 기반 에이전트 조직 구조
  - 캐릭터 애니메이션으로 작업 상태 시각화

### 1.4 핵심 차별점
| 항목 | Claw-Empire | AI Data Science Team |
|------|-------------|---------------------|
| 도메인 | 소프트웨어 개발 | **금융 데이터 사이언스** |
| 방법론 | CLI 에이전트 오케스트레이션 | **EDA → 피처 엔지니어링 → ML 모델링 → 백테스팅** |
| 예측 | 없음 | **시계열 ML 모델 (LSTM, Prophet, XGBoost)** |
| 데이터 소스 | GitHub 코드 | 한국 주식시장 (KOSPI/KOSDAQ) |
| 에이전트 역할 | 코딩 에이전트 | **데이터 엔지니어 / 데이터 사이언티스트 / ML 엔지니어** |
| 커뮤니케이션 | 인앱 메신저 | 텔레그램 봇 (1차 인터페이스) |
| 실험 관리 | 없음 | **MLflow 기반 실험 추적 & 모델 레지스트리** |

---

## 2. 시스템 요구사항

### 2.1 기능 요구사항 (Functional Requirements)

#### FR-001: 텔레그램 인터페이스
- 사용자가 텔레그램 봇을 통해 명령/대화 가능
- 지원 명령어: `/수집 [종목명]`, `/분석 [종목명]`, `/예측 [종목명]`, `/리포트 [종목명]`, `/백테스트 [종목명]`
- 수집 진행 상황 실시간 알림
- 분석 결과 요약 전송 (텍스트 + 차트 이미지)
- **ML 모델 예측 결과 + 신뢰구간** 전송

#### FR-002: 데이터 수집 시스템
- MCP + Playwright 기반 웹 스크래핑
- 대상 데이터: 주가, 공시, 재무제표, 뉴스
- 종목 카테고리: 반도체, 자동차, 바이오, IT, 에너지 등
- 시장 구분: KOSPI, KOSDAQ
- 수집 소스: DART, KRX, 네이버 금융, 한국거래소

#### FR-003: 데이터 분석 시스템 (Data Science)
- **EDA (탐색적 데이터 분석)**: 분포, 이상치, 결측치, 기초통계량 자동 분석
- **피처 엔지니어링**: 기술적 지표, 래깅 피처, 롤링 통계, 시장 피처 자동 생성
- **통계 분석**: 상관분석, 회귀분석, Granger 인과검정, 공적분 검정
- **NLP 감성 분석**: TF-IDF/임베딩 기반 감성 점수 (LLM + 통계 모델 하이브리드)
- 기술적 분석 (이동평균, RSI, MACD 등) - 피처 엔지니어링의 일부로 편입
- 기본적 분석 (PER, PBR, ROE 등) - 펀더멘털 피처로 편입

#### FR-004: 예측 시스템 (ML/DL Pipeline)
- **시계열 예측 모델**: Prophet, LSTM, GRU, Transformer
- **머신러닝 앙상블**: XGBoost, LightGBM, CatBoost
- **모델 선택 & 하이퍼파라미터 튜닝**: Optuna 기반 자동 최적화
- **앙상블 전략**: 다중 모델 가중 앙상블 (Stacking/Blending)
- **백테스팅**: 과거 데이터 기반 전략 검증 (Sharpe ratio, MDD, 수익률)
- **실험 추적**: MLflow로 모델 버전 관리 및 성능 비교
- 시나리오 분석 + 리스크 평가: 통계적 VaR, CVaR

#### FR-005: 웹 시각화
- PixiJS 기반 오피스 시뮬레이션
- 3개 팀 오피스: 수집팀, 분석팀, 예측팀
- 캐릭터 애니메이션: 수집 중, EDA 중, 모델 학습 중, 백테스팅 중 등
- 실시간 작업 상태 표시
- **ML 대시보드**: 모델 성능 비교, 예측 차트, 백테스트 결과

#### FR-006: LLM 통합
- 뉴스/공시 요약 및 감성 분석 (NLP 파이프라인의 일부)
- 자연어 쿼리 처리 (텔레그램 대화)
- **EDA 결과 해석 및 인사이트 생성**
- **ML 예측 결과를 자연어 리포트로 변환**
- 에이전트 간 커뮤니케이션

#### FR-007: 보안 및 인증
- Supabase 기반 사용자 인증
- OAuth 2.0 소셜 로그인
- API Key 암호화 저장 및 관리
- Rate limiting 및 접근 제어

### 2.2 비기능 요구사항 (Non-Functional Requirements)

#### NFR-001: 성능
- 데이터 수집 완료: 종목당 30초 이내
- EDA + 피처 엔지니어링: 종목당 15초 이내
- ML 모델 추론 (사전 학습 모델): 종목당 5초 이내
- ML 모델 학습 (재학습): 종목당 5분 이내
- 텔레그램 응답: 3초 이내
- 동시 수집 가능 종목: 10개 이상

#### NFR-002: 확장성
- 새로운 데이터 소스 추가 용이
- **새로운 ML 모델 플러그인 구조 (모델 레지스트리)**
- **피처 스토어 기반 피처 재사용**
- 종목 카테고리 동적 추가

#### NFR-003: 재현성
- **모든 실험은 MLflow로 추적 (파라미터, 메트릭, 아티팩트)**
- **모델 버전 관리 및 롤백 가능**
- **데이터 버저닝 (수집 시점별 스냅샷)**

#### NFR-004: 보안
- API 키 평문 저장 금지
- 사용자별 데이터 격리
- HTTPS 통신 강제

---

## 3. 팀 구조 설계

### 3.1 데이터 수집팀 (Data Engineering Team)
```
수집팀장 (Data Engineering Lead)
├── KOSPI 수집 에이전트
│   ├── 반도체 섹터 (삼성전자, SK하이닉스, ...)
│   ├── 자동차 섹터 (현대차, 기아, ...)
│   ├── 바이오 섹터
│   ├── IT 섹터
│   └── 에너지/화학 섹터
├── KOSDAQ 수집 에이전트
│   ├── IT/소프트웨어
│   ├── 바이오/제약
│   └── 반도체/장비
├── 공시 수집 에이전트 (DART)
├── 뉴스 수집 에이전트
└── 데이터 품질 관리 에이전트 (NEW)
    ├── 결측치 탐지 & 보간
    ├── 이상치 탐지
    └── 데이터 정합성 검증
```

### 3.2 분석팀 (Data Science Team)
```
분석팀장 (Data Science Lead)
├── EDA 에이전트 (Exploratory Data Analysis) ← NEW
│   ├── 기초통계량 & 분포 분석
│   ├── 시계열 분해 (Trend/Seasonality/Residual)
│   ├── 이상치 탐지 (IQR, Z-score, Isolation Forest)
│   └── 상관관계 & 인과관계 분석
│
├── 피처 엔지니어링 에이전트 ← NEW
│   ├── 기술적 지표 피처 (RSI, MACD, BB 등)
│   ├── 래깅/리드 피처
│   ├── 롤링 통계 피처 (이동평균, 이동표준편차)
│   ├── 펀더멘털 피처 (PER, PBR, ROE 등)
│   ├── 감성 피처 (뉴스/공시 NLP 점수)
│   └── 시장 피처 (KOSPI 수익률, 환율, 금리)
│
├── 통계 분석 에이전트 ← NEW
│   ├── 회귀 분석 (선형, 다중, 로지스틱)
│   ├── 가설 검정 (t-test, ANOVA, 비모수)
│   ├── Granger 인과검정
│   ├── 공적분 검정 (Engle-Granger, Johansen)
│   └── 변동성 모델 (GARCH, EGARCH)
│
├── 감성 분석 에이전트 (NLP + LLM 하이브리드)
│   ├── TF-IDF + 감성 사전 기반 분석
│   ├── LLM 기반 심층 감성 분석
│   └── 감성 점수 → 피처 변환
│
└── 섹터 분석 에이전트
    ├── 클러스터링 (K-Means, DBSCAN) ← NEW
    ├── PCA/t-SNE 차원축소 시각화 ← NEW
    └── 섹터 내 상대 강도
```

### 3.3 예측팀 (ML Engineering Team)
```
예측팀장 (ML Engineering Lead)
├── 모델 학습 에이전트 ← NEW
│   ├── 시계열 모델 (Prophet, ARIMA, SARIMA)
│   ├── 딥러닝 모델 (LSTM, GRU, Temporal Fusion Transformer)
│   ├── 앙상블 모델 (XGBoost, LightGBM, CatBoost)
│   └── 하이퍼파라미터 최적화 (Optuna)
│
├── 백테스팅 에이전트 ← NEW
│   ├── Walk-Forward Validation
│   ├── 전략 시뮬레이션 (매수/매도 규칙 기반)
│   ├── 성능 메트릭 (Sharpe, Sortino, MDD, Calmar)
│   └── 벤치마크 비교 (Buy & Hold vs 전략)
│
├── 리스크 평가 에이전트
│   ├── VaR (Value at Risk) - 통계적 ← UPGRADED
│   ├── CVaR (Conditional VaR) ← NEW
│   ├── 몬테카를로 시뮬레이션 ← NEW
│   └── 변동성 예측 (GARCH 기반)
│
└── 리포트 생성 에이전트 (LLM 기반)
    ├── ML 예측 결과 → 자연어 리포트 변환
    ├── 차트 이미지 생성 (matplotlib/plotly)
    ├── 텔레그램 포맷 변환
    └── 모델 성능 해석
```

---

## 4. 기술 스택

### 4.1 Backend (Python)
| 기술 | 용도 |
|------|------|
| Python 3.12+ | 메인 언어 |
| FastAPI | API 서버 |
| Supabase Python SDK | 인증 & DB |
| python-telegram-bot | 텔레그램 봇 |
| Playwright (Python) | 웹 스크래핑 |
| MCP SDK | MCP 서버/클라이언트 |
| Anthropic / OpenAI SDK | LLM 연동 |
| **Pandas / NumPy / SciPy** | **데이터 처리 & 통계 분석** |
| **scikit-learn** | **ML 모델, 전처리, 평가** |
| **XGBoost / LightGBM / CatBoost** | **앙상블 모델** |
| **PyTorch** | **LSTM, GRU, Transformer** |
| **Prophet** | **시계열 예측** |
| **statsmodels** | **통계 검정, ARIMA, GARCH** |
| **Optuna** | **하이퍼파라미터 최적화** |
| **MLflow** | **실험 추적 & 모델 레지스트리** |
| **pandas-ta / TA-Lib** | **기술적 지표 (피처 생성)** |
| **matplotlib / plotly / seaborn** | **시각화 & 차트 생성** |
| APScheduler | 스케줄링 |
| Pydantic | 데이터 검증 |
| WebSocket (websockets) | 실시간 통신 |

### 4.2 Frontend (Web Visualization)
| 기술 | 용도 |
|------|------|
| React 19 | UI 프레임워크 |
| Vite | 빌드 도구 |
| TypeScript | 타입 안전성 |
| PixiJS 8 | 2D 캐릭터 애니메이션 |
| Tailwind CSS | 스타일링 |
| **Recharts / Plotly.js** | **금융 차트 & ML 결과 시각화** |
| WebSocket | 실시간 데이터 수신 |

### 4.3 Infrastructure
| 기술 | 용도 |
|------|------|
| Supabase | 인증, DB(PostgreSQL), Storage |
| **MLflow** | **실험 관리, 모델 레지스트리** |
| Docker | 컨테이너화 |
| Railway / Fly.io | 배포 |

---

## 5. 데이터 모델

### 5.1 핵심 엔티티

```
-- 기존 테이블 유지 (stocks, stock_prices, disclosures, news, telegram_sessions) --

features (피처 스토어) ← NEW
├── id: UUID
├── stock_id: FK → stocks
├── date: DATE
├── feature_set: VARCHAR (e.g., "technical", "fundamental", "sentiment", "market")
├── features: JSONB (피처 이름-값 쌍)
├── version: INTEGER (피처 버전)
└── created_at: TIMESTAMP

ml_experiments (실험 추적) ← NEW
├── id: UUID
├── experiment_name: VARCHAR
├── model_type: VARCHAR (prophet, lstm, xgboost, ensemble, ...)
├── stock_id: FK → stocks (nullable, 섹터 모델이면 null)
├── hyperparameters: JSONB
├── metrics: JSONB (RMSE, MAE, MAPE, Sharpe, MDD 등)
├── feature_columns: JSONB (사용된 피처 목록)
├── mlflow_run_id: VARCHAR
├── status: ENUM (running, completed, failed)
├── created_at: TIMESTAMP
└── duration_seconds: INTEGER

ml_models (모델 레지스트리) ← NEW
├── id: UUID
├── experiment_id: FK → ml_experiments
├── model_name: VARCHAR
├── model_version: INTEGER
├── model_path: VARCHAR (Storage 경로)
├── stage: ENUM (staging, production, archived)
├── metrics: JSONB
├── created_at: TIMESTAMP
└── promoted_at: TIMESTAMP

predictions (ML 예측 결과) ← NEW (기존 forecasts 대체)
├── id: UUID
├── stock_id: FK → stocks
├── model_id: FK → ml_models
├── prediction_date: DATE (예측 실행일)
├── target_date: DATE (예측 대상일)
├── predicted_price: DECIMAL
├── confidence_interval_lower: DECIMAL (95% CI)
├── confidence_interval_upper: DECIMAL (95% CI)
├── predicted_direction: ENUM (up, down, neutral)
├── direction_probability: DECIMAL
├── features_used: JSONB (snapshot)
└── created_at: TIMESTAMP

backtests (백테스팅 결과) ← NEW
├── id: UUID
├── model_id: FK → ml_models
├── stock_id: FK → stocks
├── start_date: DATE
├── end_date: DATE
├── strategy: VARCHAR
├── metrics: JSONB (수익률, Sharpe, MDD, win_rate 등)
├── trade_log: JSONB (매매 기록)
└── created_at: TIMESTAMP

eda_reports (EDA 결과) ← NEW
├── id: UUID
├── stock_id: FK → stocks
├── report_type: VARCHAR (distribution, correlation, decomposition, outlier)
├── result: JSONB
├── charts: JSONB (차트 이미지 경로 목록)
├── insights: TEXT (LLM 생성 인사이트)
└── created_at: TIMESTAMP

analyses (분석 결과) - UPDATED
├── id: UUID
├── stock_id: FK → stocks
├── analysis_type: ENUM (eda, statistical, sentiment, sector, feature_importance)
├── result: JSONB
├── agent_id: VARCHAR
├── created_at: TIMESTAMP
└── confidence_score: DECIMAL

agent_tasks (에이전트 작업)
├── id: UUID
├── agent_type: VARCHAR (data_engineer, data_scientist, ml_engineer)
├── agent_name: VARCHAR
├── task_type: VARCHAR
├── status: ENUM (pending, running, completed, failed)
├── input_params: JSONB
├── output_result: JSONB
├── started_at: TIMESTAMP
├── completed_at: TIMESTAMP
└── error_message: TEXT
```

---

## 6. 데이터 사이언스 파이프라인 (핵심)

### 6.1 전체 파이프라인

```
[데이터 수집]                     [데이터 사이언스]                    [ML 엔지니어링]

Raw Data     →  Clean Data   →   EDA          →  Feature Store  →  Model Training
(스크래핑)       (전처리)         (탐색적 분석)     (피처 저장)        (모델 학습)
                                    │                                    │
                                    ▼                                    ▼
                              Statistical       Feature          Model Selection
                              Analysis          Engineering      & Tuning
                              (통계 검정)        (피처 생성)       (최적화)
                                    │                                    │
                                    ▼                                    ▼
                              Sentiment         Feature          Backtesting
                              Analysis          Selection        (백테스팅)
                              (감성 분석)        (피처 선택)           │
                                                                      ▼
                                                                 Prediction
                                                                 (예측 실행)
                                                                      │
                                                                      ▼
                                                              Report Generation
                                                              (리포트: LLM)
                                                                      │
                                                                      ▼
                                                              [텔레그램 전송]
```

### 6.2 기존 vs 개선 비교

```
Before (증권 분석 시스템)              After (데이터 사이언스 시스템)
──────────────────────               ──────────────────────────
RSI 값 계산 → "과매수"               RSI 피처 생성 → ML 입력 변수
PER 비교 → "저평가"                  PER 피처 + 동종업계 z-score → ML 입력
LLM에게 "전망해줘"                   LSTM/XGBoost → 확률적 가격 예측 + 신뢰구간
감성: LLM이 점수 매기기              TF-IDF 벡터 + LLM 임베딩 → 감성 피처 → ML 입력
없음                                 Optuna로 하이퍼파라미터 자동 최적화
없음                                 Walk-Forward 백테스팅 → Sharpe/MDD 평가
없음                                 MLflow로 실험 추적 → 최적 모델 자동 선택
```

---

## 7. 사용자 시나리오 (User Flow)

### 시나리오 1: 삼성전자 분석 요청

```
1. 사용자 → 텔레그램: "/분석 삼성전자"
2. 봇 → 텔레그램: "삼성전자(005930) 데이터 사이언스 분석을 시작합니다."
3. [웹 시각화] 수집팀 캐릭터 활성화

4. 수집팀 → 데이터 수집 + 전처리
   - 주가 (120일), 공시, 뉴스 수집
   - 결측치 보간, 이상치 플래깅

5. 봇 → "데이터 수집 완료! 분석팀에 전달합니다."
6. [웹 시각화] 서류 배달 → 분석팀

7. 분석팀 → 데이터 사이언스 분석
   a) EDA 에이전트: 분포 분석, 시계열 분해, 이상치 탐지
   b) 피처 엔지니어링: 50+ 피처 생성 (기술적/펀더멘털/감성/시장)
   c) 통계 분석: 상관관계, Granger 인과, GARCH 변동성
   d) 감성 분석: 뉴스 NLP + LLM 하이브리드

8. 봇 → "분석 완료! (50개 피처 생성, 주요 인사이트 3건) 예측팀에 전달합니다."
9. [웹 시각화] 서류 배달 → 예측팀

10. 예측팀 → ML 예측
    a) 모델 학습: Prophet + LSTM + XGBoost (3개 모델 병렬)
    b) 앙상블: 가중 평균 예측
    c) 백테스팅: 최근 30일 Walk-Forward
    d) 리스크: VaR, CVaR, 몬테카를로

11. 봇 → 텔레그램: 최종 리포트 전송
    - ML 예측: 1주 후 78,500원 (95% CI: 75,200~81,800)
    - 모델 성능: MAPE 2.3%, 방향 정확도 68%
    - 백테스트: Sharpe 1.45, MDD -8.2%
    - 리스크: VaR(95%) = -4.2%
```

### 시나리오 2: 백테스트 요청

```
1. 사용자 → 텔레그램: "/백테스트 삼성전자 3개월"
2. 봇: "3개월 백테스팅을 실행합니다..."
3. 예측팀 → Walk-Forward 백테스팅 실행
4. 봇: 백테스트 결과 리포트 전송
   - 누적 수익률 차트
   - Sharpe ratio, MDD, Win rate
   - Buy & Hold 대비 성과
```

---

## 8. 구현 단계 (Implementation Phases)

### Phase 1: 기반 인프라 (2주)
- [ ] 프로젝트 구조 설정 (Python 패키지 구조)
- [ ] Supabase 프로젝트 생성 및 스키마 설정
- [ ] 기본 FastAPI 서버 구축
- [ ] 텔레그램 봇 기본 연결
- [ ] 보안 모듈 (API Key 관리, 인증)
- [ ] **MLflow 서버 설정**

### Phase 2: 데이터 수집팀 구현 (2주)
- [ ] MCP 서버 설정
- [ ] Playwright 기반 스크래퍼 구현
- [ ] 종목 데이터 수집 (주가, 공시, 뉴스)
- [ ] **데이터 품질 관리 (결측치/이상치 탐지)**
- [ ] 수집 스케줄러 구현

### Phase 3: 분석팀 구현 - 데이터 사이언스 (3주)
- [ ] **EDA 자동화 모듈 (분포, 시계열 분해, 상관분석)**
- [ ] **피처 엔지니어링 파이프라인 (50+ 피처)**
- [ ] **피처 스토어 구현**
- [ ] **통계 분석 모듈 (가설검정, Granger, GARCH)**
- [ ] NLP 감성 분석 (TF-IDF + LLM 하이브리드)

### Phase 4: 예측팀 구현 - ML 엔지니어링 (3주)
- [ ] **시계열 모델 구현 (Prophet, ARIMA)**
- [ ] **딥러닝 모델 구현 (LSTM, Transformer)**
- [ ] **앙상블 모델 구현 (XGBoost, LightGBM)**
- [ ] **Optuna 하이퍼파라미터 최적화**
- [ ] **백테스팅 프레임워크 구현**
- [ ] **MLflow 실험 추적 연동**
- [ ] 리포트 생성기 (ML 결과 → LLM → 자연어)

### Phase 5: 웹 시각화 (2주)
- [ ] React + PixiJS 프로젝트 설정
- [ ] 오피스 씬 구현 (3개 팀룸)
- [ ] 캐릭터 애니메이션 구현
- [ ] WebSocket 실시간 연동
- [ ] **ML 대시보드 (모델 성능, 예측 차트, 백테스트)**

### Phase 6: 통합 및 최적화 (1주)
- [ ] 전체 플로우 통합 테스트
- [ ] 성능 최적화
- [ ] 에러 처리 강화
- [ ] 배포

---

## 9. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 웹 스크래핑 차단 | 데이터 수집 불가 | 다중 소스, User-Agent 로테이션, API 우선 사용 |
| LLM API 비용 | 운영비 증가 | 캐싱, 요약 단계적 처리, 무료 모델 병행 |
| **ML 모델 과적합** | **예측 정확도 저하** | **Walk-Forward CV, 정규화, 앙상블** |
| **학습 데이터 부족** | **모델 성능 저하** | **섹터 모델(여러 종목 통합), 전이학습** |
| **모델 학습 시간** | **응답 지연** | **사전 학습 + 캐시, 경량 모델 우선** |
| 실시간 데이터 지연 | 분석 정확도 저하 | 데이터 타임스탬프 관리, 지연 허용치 설정 |
| Supabase 무료 한도 | 서비스 중단 | 사용량 모니터링, 중요 데이터 로컬 캐시 |

---

## 10. 폴더별 상세 기획서 구조

```
docs/
├── PRD/
│   └── PRD.md                      ← 현재 문서
├── 01_시스템_아키텍처/
│   └── architecture.md              ← 전체 시스템 아키텍처 + ML 파이프라인
├── 02_데이터_수집팀/
│   └── data_collection_team.md      ← 수집팀 상세 설계
├── 03_분석팀/
│   └── analysis_team.md             ← 데이터 사이언스 분석팀 상세 설계
├── 04_전망팀/
│   └── forecast_team.md             ← ML 엔지니어링 예측팀 상세 설계
├── 05_텔레그램_연동/
│   └── telegram_integration.md      ← 텔레그램 봇 설계
├── 06_웹_시각화/
│   └── web_visualization.md         ← 웹 시각화 설계
├── 07_보안_인증/
│   └── security_auth.md             ← 보안 및 인증 설계
├── 08_LLM_연동/
│   └── llm_integration.md           ← LLM 통합 설계
└── 09_배포_운영/
    └── deployment.md                ← 배포 및 운영 가이드
```
