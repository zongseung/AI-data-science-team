# AI Data Science Team - MSA Services

## 🏗️ Microservice Architecture

이 디렉토리는 **docs 기반 8개 마이크로서비스**로 구성되어 있습니다.

```
src/
├── shared/                    # 공통 코드
├── krx-service/              # Service 1: KRX 공매도 수집
├── collection-service/       # Service 2: 데이터 수집 (네이버/DART)
├── analysis-service/         # Service 3: 분석팀 (EDA/피처/통계)
├── forecast-service/         # Service 4: 전망팀 (ML/백테스트)
├── report-service/           # Service 5: 보고서팀
├── telegram-service/         # Service 6: 텔레그램 봇
├── web-service/              # Service 7: React + PixiJS UI
└── api-gateway/              # Service 8: Nginx 게이트웨이
```

---

## 📋 서비스 목록

| 서비스 | 포트 | 역할 | 문서 참조 |
|--------|------|------|----------|
| krx-service | 8001 | KRX 공매도 데이터 수집 | - |
| collection-service | 8002 | 네이버/DART 데이터 수집 | docs/02_데이터_수집팀/ |
| analysis-service | 8003 | EDA/피처/통계/감성/섹터 분석 | docs/03_분석팀/ |
| forecast-service | 8004 | ML 학습/백테스트/리스크 | docs/04_전망팀/ |
| report-service | 8005 | 보고서/투자메모/리스크노트 | docs/04-1_보고서팀/ |
| telegram-service | 8006 | 텔레그램 봇 인터페이스 | docs/05_텔레그램_연동/ |
| web-service | 3000 | React + PixiJS 웹 UI | docs/06_웹_시각화/ |
| api-gateway | 80 | Nginx API 게이트웨이 | - |

---

## 🚀 빠른 시작

### 1. 전체 서비스 실행 (Docker Compose)
```bash
cd src
docker-compose up -d
```

### 2. 개별 서비스 실행
```bash
# KRX 서비스
cd krx-service
uv run uvicorn app.api:app --port 8001

# Collection 서비스
cd collection-service
uv run uvicorn app.main:app --port 8002
```

---

## 📦 공통 모듈 (shared/)

모든 서비스에서 사용하는 공통 코드:

- **config/**: 설정 (constants, settings, prefect_config)
- **utils/**: 유틸리티 (event_bus, storage)

```python
# 다른 서비스에서 import
from shared.config.constants import STOCK_CODES
from shared.utils.event_bus import event_bus
```

---

## 🔗 서비스 간 통신

### HTTP REST API
```
collection-service → krx-service (HTTP)
analysis-service → collection-service (HTTP)
forecast-service → analysis-service (HTTP)
report-service → forecast-service (HTTP)
```

### Event Bus (WebSocket)
```
모든 서비스 → event_bus → web-service (WebSocket)
```

---

## 📝 각 서비스 상세

### 1. krx-service
**역할**: KRX 공매도 데이터 수집
- [README](./krx-service/README.md)
- 기술: FastAPI + httpx + pandas
- 독립 실행 가능

### 2. collection-service
**역할**: 네이버 금융 + DART + 뉴스 + 시장 데이터 수집
- [README](./collection-service/README.md)
- 기술: Prefect + Playwright + httpx
- 의존성: krx-service

### 3. analysis-service
**역할**: EDA, 피처 엔지니어링, 통계, 감성, 섹터 분석
- [README](./analysis-service/README.md)
- 기술: Pandas + NumPy + scikit-learn + LLM
- 의존성: collection-service

### 4. forecast-service
**역할**: ML 모델 학습, 백테스트, 리스크 평가
- [README](./forecast-service/README.md)
- 기술: XGBoost + LightGBM + Prophet + LSTM + MLflow
- 의존성: analysis-service

### 5. report-service
**역할**: 종합 보고서, 투자 메모, 리스크 노트 생성
- [README](./report-service/README.md)
- 기술: LLM (GPT-4/Claude)
- 의존성: analysis-service + forecast-service

### 6. telegram-service
**역할**: 텔레그램 봇 인터페이스
- [README](./telegram-service/README.md)
- 기술: python-telegram-bot
- 의존성: 모든 서비스 (오케스트레이션)

### 7. web-service
**역할**: 웹 UI (PixiJS 애니메이션)
- [README](./web-service/README.md)
- 기술: React 19 + PixiJS 8 + TypeScript
- 의존성: api-gateway (WebSocket)

### 8. api-gateway
**역할**: 라우팅 + 로드밸런싱
- [README](./api-gateway/README.md)
- 기술: Nginx
- 의존성: 모든 서비스

---

## 🛠️ 개발 가이드

### 새 서비스 추가
```bash
mkdir -p src/new-service/{app,tests}
touch src/new-service/Dockerfile
touch src/new-service/requirements.txt
```

### 공통 코드 수정
```bash
# shared/ 수정 후 모든 서비스 재시작
cd src
docker-compose restart
```

---

## 📊 구현 상태

| 서비스 | 상태 | 진행률 |
|--------|------|--------|
| shared | ✅ 완료 | 100% |
| krx-service | ✅ 완료 | 100% |
| collection-service | 🚧 진행중 | 80% |
| analysis-service | ⬜ 예정 | 20% |
| forecast-service | ⬜ 예정 | 20% |
| report-service | ⬜ 예정 | 20% |
| telegram-service | ⬜ 예정 | 0% |
| web-service | ⬜ 예정 | 0% |
| api-gateway | ⬜ 예정 | 0% |

---

## 📖 참고 문서

- [MSA 구조 상세](./MSA_STRUCTURE.md)
- [프로젝트 아키텍처](../PROJECT_ARCHITECTURE.md)
- [기술 문서](../docs/)
