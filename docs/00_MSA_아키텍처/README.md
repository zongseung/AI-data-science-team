# MSA 아키텍처 (2026년 3월 업데이트)

## 🏗️ 전체 구조 변경 사항

### 이전 (Monolithic)
```
ai_data_science_team/    # 단일 패키지
├── collectors/
├── agents/
├── flows/
└── api/
```

### 현재 (MSA)
```
src/                     # 마이크로서비스 기반
├── shared/              # 공통 모듈
├── krx-service/         # Service 1: KRX 수집
├── collection-service/  # Service 2: 데이터 수집
├── analysis-service/    # Service 3: 분석팀
├── forecast-service/    # Service 4: 전망팀
├── report-service/      # Service 5: 보고서팀
├── telegram-service/    # Service 6: 텔레그램
├── web-service/         # Service 7: 웹 UI
└── api-gateway/         # Service 8: API 게이트웨이
```

---

## 📋 서비스별 포트 및 역할

| 서비스 | 포트 | 역할 | 문서 |
|--------|------|------|------|
| krx-service | 8001 | KRX 공매도 데이터 수집 | - |
| collection-service | 8002 | 네이버/DART 데이터 수집 오케스트레이션 | [02_데이터_수집팀](../02_데이터_수집팀/) |
| analysis-service | 8003 | EDA/피처/통계/감성/섹터 분석 | [03_분석팀](../03_분석팀/) |
| forecast-service | 8004 | ML 학습/백테스트/리스크 평가 | [04_전망팀](../04_전망팀/) |
| report-service | 8005 | 보고서 생성 (종합/투자메모/리스크노트) | [04-1_보고서팀](../04-1_보고서팀/) |
| telegram-service | 8006 | 텔레그램 봇 인터페이스 | [05_텔레그램_연동](../05_텔레그램_연동/) |
| web-service | 3000 | React + PixiJS 웹 UI | [06_웹_시각화](../06_웹_시각화/) |
| api-gateway | 80 | Nginx 게이트웨이 | - |

---

## 🔄 데이터 흐름

```
[사용자]
   ↓
[api-gateway :80] ────────────────────┐
   ├─→ [web-service :3000]           │
   ├─→ [telegram-service :8006]      │
   │                                  │
   ├─→ [collection-service :8002] ───┼─→ [krx-service :8001]
   │      ↓                           │
   ├─→ [analysis-service :8003]      │
   │      ↓                           │
   ├─→ [forecast-service :8004]      │
   │      ↓                           │
   └─→ [report-service :8005]        │
          ↓                           │
   [Supabase] ←─────────────────────┘
   [Telegram API]
   [WebSocket]
```

---

## 🚀 주요 변경 사항

### 1. MCP 제거
- **이전**: MCP (Model Context Protocol) 기반 도구 관리
- **현재**: 직접 스크래퍼 + Prefect 오케스트레이션
- **이유**: 데이터 수집은 확정적 파이프라인, LLM 불필요

### 2. 서비스 분리
- **이전**: 단일 FastAPI 애플리케이션
- **현재**: 8개 독립 마이크로서비스
- **이유**: 독립 배포, 스케일링, 기술 스택 분리

### 3. Prefect 도입
- **이전**: APScheduler
- **현재**: Prefect 3.x
- **이유**: 강력한 워크플로우 오케스트레이션, 재시도, 모니터링

---

## 📦 Docker Compose 실행

```bash
cd src
docker-compose up -d
```

서비스 접속:
- API Gateway: http://localhost
- Web UI: http://localhost:3000
- Prefect UI: http://localhost:4200

---

## 📖 문서 참조

각 서비스의 상세 설계는 원래 문서를 참조하되, 경로는 다음과 같이 변경:

| 구 경로 | 신 경로 |
|---------|---------|
| `ai_data_science_team/collectors/` | `src/collection-service/app/collectors/` |
| `ai_data_science_team/agents/analysis/` | `src/analysis-service/app/agents/` |
| `ai_data_science_team/agents/forecast/` | `src/forecast-service/app/agents/` |
| `ai_data_science_team/agents/report/` | `src/report-service/app/agents/` |
| `ai_data_science_team/flows/` | 각 서비스의 `app/flows/` |
| `ai_data_science_team/api/` | `src/api-gateway/app/` |

---

## 🔗 관련 문서

- [MSA 구조 상세](../../src/MSA_STRUCTURE.md)
- [프로젝트 아키텍처](../../PROJECT_ARCHITECTURE.md)
- [기존 시스템 아키텍처](../01_시스템_아키텍처/architecture.md) (참고용)
