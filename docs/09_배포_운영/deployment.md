# 09. 배포 및 운영 상세 설계

## 1. 배포 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    배포 환경                                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Docker Compose (개발/스테이징)                         │   │
│  │                                                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │   │
│  │  │ Backend  │  │ Frontend │  │ Playwright   │        │   │
│  │  │ (FastAPI)│  │ (Vite)   │  │ (Browser)    │        │   │
│  │  │ :8000    │  │ :5173    │  │              │        │   │
│  │  └──────────┘  └──────────┘  └──────────────┘        │   │
│  │                                                        │   │
│  │  ┌──────────┐  ┌──────────────────────────────┐      │   │
│  │  │ MLflow   │  │ ML Worker (모델 학습 전용)      │      │   │
│  │  │ :5000    │  │ Optuna + PyTorch + XGBoost    │      │   │
│  │  └──────────┘  └──────────────────────────────┘      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  프로덕션 (Cloud)                                      │   │
│  │                                                        │   │
│  │  Backend: Railway / Fly.io / AWS ECS                  │   │
│  │  ML Worker: Railway (GPU) / AWS SageMaker             │   │
│  │  MLflow: Railway / Self-hosted                        │   │
│  │  Frontend: Vercel / Cloudflare Pages                  │   │
│  │  DB: Supabase (Managed PostgreSQL)                    │   │
│  │  Storage: Supabase Storage (모델 아티팩트 포함)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 2. Docker 설정

### 2.1 Backend Dockerfile

```dockerfile
# Dockerfile.backend

FROM python:3.12-slim

# Playwright 시스템 의존성
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 설치 (ML 라이브러리 포함)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Playwright 브라우저 설치
RUN playwright install chromium

# ML 아티팩트 디렉토리
RUN mkdir -p /app/ml_artifacts /app/mlflow

# 소스 코드 복사
COPY . .

# 환경변수
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

EXPOSE 8000

CMD ["uvicorn", "ai_data_science_team.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 Frontend Dockerfile

```dockerfile
# Dockerfile.frontend

FROM node:22-slim AS build

WORKDIR /app
COPY web/package.json web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY web/ .
RUN pnpm build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

### 2.3 Docker Compose

```yaml
# docker-compose.yml

version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  # MLflow 추적 서버
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.19.0
    ports:
      - "5000:5000"
    volumes:
      - ./mlflow:/mlflow
    command: >
      mlflow server
      --host 0.0.0.0
      --port 5000
      --backend-store-uri sqlite:///mlflow/mlflow.db
      --default-artifact-root /mlflow/artifacts
    restart: unless-stopped

  # ML Worker (모델 학습 전용, 리소스 집약적 작업 분리)
  ml-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: python -m ai_data_science_team.ml_worker
    env_file:
      - .env
    environment:
      - MLFLOW_TRACKING_URI=http://mlflow:5000
    volumes:
      - ./ml_artifacts:/app/ml_artifacts
    depends_on:
      - mlflow
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
    restart: unless-stopped

  # 개발 환경에서만 사용
  dev-backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    command: uvicorn ai_data_science_team.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - .:/app
    profiles:
      - dev

  dev-frontend:
    image: node:22-slim
    working_dir: /app
    command: sh -c "corepack enable && pnpm install && pnpm dev --host"
    ports:
      - "5173:5173"
    volumes:
      - ./web:/app
    profiles:
      - dev
```

## 3. CI/CD 파이프라인

### 3.1 GitHub Actions

```yaml
# .github/workflows/ci.yml

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          playwright install chromium

      - name: Lint
        run: ruff check .

      - name: Type check
        run: mypy ai_data_science_team/

      - name: Test
        run: pytest tests/ -v --cov=ai_data_science_team

      - name: Test ML Pipeline
        run: pytest tests/ml/ -v --cov=ai_data_science_team.agents

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"

      - name: Install dependencies
        working-directory: web
        run: |
          corepack enable
          pnpm install --frozen-lockfile

      - name: Lint
        working-directory: web
        run: pnpm lint

      - name: Type check
        working-directory: web
        run: pnpm tsc --noEmit

      - name: Test
        working-directory: web
        run: pnpm test

      - name: Build
        working-directory: web
        run: pnpm build

  deploy:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      # Railway 배포 (백엔드)
      - name: Deploy Backend to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: backend

      # Vercel 배포 (프론트엔드)
      - name: Deploy Frontend to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: web
```

## 4. 모니터링

### 4.1 헬스체크 API

```python
# api/v1/health.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """서비스 헬스체크"""
    checks = {
        "status": "healthy",
        "supabase": await check_supabase(),
        "telegram": await check_telegram_bot(),
        "llm": await check_llm_availability(),
        "playwright": await check_playwright(),
        "mlflow": await check_mlflow_connection(),
        "ml_worker": await check_ml_worker_status(),
        "report_agents": await check_report_agents_status(),  # 보고서팀 상태
        "feature_store": await check_feature_store(),
    }

    all_healthy = all(
        v == "ok" for k, v in checks.items() if k != "status"
    )
    checks["status"] = "healthy" if all_healthy else "degraded"

    return checks
```

### 4.2 로깅 구조

```python
# utils/logger.py

import logging
import json
from datetime import datetime


class StructuredLogger:
    """구조화된 JSON 로거"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def info(self, message: str, **kwargs):
        self.logger.info(message, extra={"data": kwargs})

    def error(self, message: str, **kwargs):
        self.logger.error(message, extra={"data": kwargs})


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "data"):
            log_entry.update(record.data)
        return json.dumps(log_entry, ensure_ascii=False)


# 사용 예시
logger = StructuredLogger("ai_finance")
logger.info("수집 완료", stock_code="005930", items_count=120, duration_ms=15000)
```

### 4.3 메트릭 대시보드

```python
# 추적할 메트릭
METRICS = {
    # 수집 메트릭
    "collection_count": "수집된 데이터 건수",
    "collection_duration": "수집 소요 시간 (ms)",
    "collection_errors": "수집 실패 횟수",
    "scraping_blocked": "스크래핑 차단 횟수",

    # EDA/분석 메트릭
    "eda_count": "EDA 실행 횟수",
    "eda_duration": "EDA 소요 시간 (ms)",
    "feature_count": "생성된 피처 수",
    "feature_selection_ratio": "피처 선택 비율 (%)",
    "analysis_count": "분석 실행 횟수",
    "analysis_duration": "분석 소요 시간 (ms)",

    # ML 메트릭
    "model_training_count": "모델 학습 횟수",
    "model_training_duration": "모델 학습 소요 시간 (ms)",
    "model_avg_mape": "평균 MAPE (%)",
    "model_avg_direction_accuracy": "평균 방향 정확도 (%)",
    "optuna_trials_total": "Optuna 총 Trial 수",
    "backtest_count": "백테스트 실행 횟수",
    "backtest_avg_sharpe": "평균 Sharpe Ratio",
    "mlflow_experiments": "MLflow 등록 실험 수",
    "mlflow_registered_models": "MLflow 등록 모델 수",
    "prediction_count": "예측 실행 횟수",

    # 보고서팀 메트릭 ← NEW
    "report_count": "보고서 생성 횟수",
    "report_duration": "보고서 작성 소요 시간 (ms)",
    "report_review_pass_rate": "편집장 검토 통과율 (%)",
    "report_delivery_count": "텔레그램 발송 완료 횟수",

    # LLM 메트릭
    "llm_requests": "LLM API 호출 횟수",
    "llm_tokens": "총 사용 토큰 수",
    "llm_cost": "LLM 비용 (USD)",
    "llm_cache_hit_rate": "캐시 적중률 (%)",

    # 텔레그램 메트릭
    "telegram_messages": "수신 메시지 수",
    "telegram_responses": "발송 메시지 수",
    "telegram_avg_response_time": "평균 응답 시간 (ms)",

    # 시스템 메트릭
    "active_agents": "활성 에이전트 수",
    "task_queue_length": "대기 중 작업 수",
    "websocket_connections": "WebSocket 연결 수",
    "ml_worker_memory_usage": "ML Worker 메모리 사용량 (MB)",
    "ml_worker_cpu_usage": "ML Worker CPU 사용률 (%)",
}
```

## 5. 스케줄링

### 5.1 정기 작업 스케줄

```python
# core/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler


def setup_scheduler(orchestrator: Orchestrator) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # 매일 장마감 후 전종목 데이터 수집 (16:00)
    scheduler.add_job(
        orchestrator.daily_collection,
        "cron",
        hour=16,
        minute=0,
        timezone="Asia/Seoul",
        id="daily_collection",
    )

    # 장중 주요 종목 시세 확인 (09:30 ~ 15:20, 10분 간격)
    scheduler.add_job(
        orchestrator.check_market_prices,
        "cron",
        hour="9-15",
        minute="*/10",
        timezone="Asia/Seoul",
        id="market_check",
    )

    # 공시 확인 (매 1시간)
    scheduler.add_job(
        orchestrator.check_disclosures,
        "interval",
        hours=1,
        id="disclosure_check",
    )

    # 뉴스 수집 (매 30분)
    scheduler.add_job(
        orchestrator.collect_news,
        "interval",
        minutes=30,
        id="news_collection",
    )

    # 매일 장마감 후 피처 엔지니어링 & 모델 재학습 (16:30)
    scheduler.add_job(
        orchestrator.daily_feature_engineering,
        "cron",
        hour=16,
        minute=30,
        timezone="Asia/Seoul",
        id="daily_feature_engineering",
    )

    # 매일 모델 재학습 (관심 종목 대상, 17:00)
    scheduler.add_job(
        orchestrator.daily_model_retrain,
        "cron",
        hour=17,
        minute=0,
        timezone="Asia/Seoul",
        id="daily_model_retrain",
    )

    # 일일 보고서팀 리포트 작성 & 전송 (17:30)
    scheduler.add_job(
        orchestrator.generate_daily_reports,  # 보고서팀이 종합 리포트 작성
        "cron",
        hour=17,
        minute=30,
        timezone="Asia/Seoul",
        id="daily_report_generation",
    )

    # 일일 리포트 전송 (18:00, 편집장 승인 후)
    scheduler.add_job(
        orchestrator.send_daily_reports,
        "cron",
        hour=18,
        minute=0,
        timezone="Asia/Seoul",
        id="daily_report",
    )

    # 예측 정확도 추적 - 실제값 대비 예측값 비교 (매일 16:10)
    scheduler.add_job(
        orchestrator.evaluate_prediction_accuracy,
        "cron",
        hour=16,
        minute=10,
        timezone="Asia/Seoul",
        id="prediction_evaluation",
    )

    # 모델 드리프트 감지 (매주 월요일 06:00)
    scheduler.add_job(
        orchestrator.check_model_drift,
        "cron",
        day_of_week="mon",
        hour=6,
        minute=0,
        timezone="Asia/Seoul",
        id="model_drift_check",
    )

    # MLflow 아티팩트 정리 (매주 일요일 03:00, 오래된 실험 삭제)
    scheduler.add_job(
        orchestrator.cleanup_mlflow_artifacts,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        timezone="Asia/Seoul",
        id="mlflow_cleanup",
    )

    # LLM 비용 일일 보고 (23:00)
    scheduler.add_job(
        orchestrator.report_daily_costs,
        "cron",
        hour=23,
        minute=0,
        timezone="Asia/Seoul",
        id="cost_report",
    )

    return scheduler
```

## 6. 환경별 설정

```python
# config/environments.py

ENVIRONMENTS = {
    "development": {
        "debug": True,
        "cors_origins": ["http://localhost:5173", "http://localhost:3000"],
        "rate_limit_multiplier": 10,  # 개발 시 제한 완화
        "llm_model_override": "fast",  # 비용 절약
        "log_level": "DEBUG",
        "mlflow_tracking_uri": "http://localhost:5000",
        "ml_model_max_epochs": 10,    # 개발 시 빠른 학습
        "optuna_n_trials": 5,         # 개발 시 적은 Trial
        "ml_worker_memory_limit": "2G",
    },
    "staging": {
        "debug": False,
        "cors_origins": ["https://staging.example.com"],
        "rate_limit_multiplier": 1,
        "llm_model_override": None,
        "log_level": "INFO",
        "mlflow_tracking_uri": "http://mlflow:5000",
        "ml_model_max_epochs": 30,
        "optuna_n_trials": 15,
        "ml_worker_memory_limit": "4G",
    },
    "production": {
        "debug": False,
        "cors_origins": ["https://example.com"],
        "rate_limit_multiplier": 1,
        "llm_model_override": None,
        "log_level": "WARNING",
        "mlflow_tracking_uri": "http://mlflow:5000",
        "ml_model_max_epochs": 50,
        "optuna_n_trials": 30,
        "ml_worker_memory_limit": "8G",
    },
}
```

## 7. 백업 및 복구

```python
# 백업 전략
BACKUP_STRATEGY = {
    "database": {
        "method": "Supabase 자동 백업 (프로 플랜)",
        "frequency": "매일",
        "retention": "30일",
        "point_in_time_recovery": True,
    },
    "ml_artifacts": {
        "method": "Supabase Storage + 버전별 스냅샷",
        "frequency": "모델 학습 완료 시마다",
        "retention": "최근 5개 버전",
        "includes": ["모델 가중치", "스케일러", "피처 목록", "하이퍼파라미터"],
    },
    "mlflow_db": {
        "method": "SQLite DB 백업",
        "frequency": "매일",
        "retention": "14일",
    },
    "logs": {
        "method": "로그 파일 로테이션",
        "max_size": "100MB",
        "max_files": 10,
        "compress": True,
    },
    "config": {
        "method": "Git 버전 관리",
        "exclude": [".env", "*.key", "*.pem", "ml_artifacts/"],
    },
}
```

## 8. 운영 체크리스트

### 8.1 배포 전 체크리스트

```
[ ] 모든 테스트 통과
[ ] 환경변수 설정 완료
[ ] DB 마이그레이션 실행
[ ] Supabase RLS 정책 확인
[ ] SSL 인증서 확인
[ ] Rate Limiting 설정 확인
[ ] 로깅 레벨 확인
[ ] 헬스체크 엔드포인트 동작 확인
[ ] LLM API 키 유효성 확인
[ ] 텔레그램 봇 토큰 유효성 확인
[ ] DART API 키 유효성 확인
[ ] Playwright 브라우저 설치 확인
[ ] MLflow 서버 정상 기동 확인
[ ] ML Worker 프로세스 정상 실행 확인
[ ] ML 라이브러리 버전 호환성 확인 (PyTorch, XGBoost, scikit-learn)
[ ] 모델 아티팩트 저장 경로 쓰기 권한 확인
[ ] 피처 스토어 초기 데이터 존재 확인
```

### 8.2 운영 중 모니터링

```
매일:
[ ] 헬스체크 상태 확인 (MLflow, ML Worker 포함)
[ ] LLM 비용 확인 (일일 예산 대비)
[ ] 에러 로그 검토
[ ] 수집 실패율 확인
[ ] ML 예측 정확도 확인 (전일 예측 vs 실제)
[ ] 모델 재학습 정상 완료 확인
[ ] ML Worker 메모리/CPU 사용량 확인

매주:
[ ] 성능 메트릭 리뷰
[ ] 스크래핑 차단 여부 확인
[ ] ML 모델 성능 드리프트 확인
[ ] MLflow 실험 로그 리뷰
[ ] 피처 중요도 변화 추적
[ ] 사용자 피드백 검토
[ ] 의존성 보안 업데이트 확인

매월:
[ ] 전체 비용 리뷰 (LLM + ML 인프라)
[ ] 사용량 추세 분석
[ ] ML 모델 전체 재학습 (전체 데이터 사용)
[ ] 백테스트 전략 성과 재평가
[ ] MLflow 아티팩트 정리 (불필요 실험 삭제)
[ ] 인프라 확장 필요성 검토
[ ] 보안 감사
```

## 9. Graceful Shutdown

```python
# core/lifecycle.py

import signal
import asyncio


class AppLifecycle:
    """애플리케이션 생명주기 관리"""

    def __init__(self):
        self.shutting_down = False
        self.active_tasks: set[asyncio.Task] = set()

    def setup_signal_handlers(self):
        """시그널 핸들러 등록"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Graceful shutdown 시작"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutting_down = True
        asyncio.create_task(self._shutdown())

    async def _shutdown(self):
        """정리 작업 실행"""
        # 1. 새 작업 수락 중단
        logger.info("Stopping new task acceptance...")

        # 2. 진행 중인 작업 완료 대기 (최대 30초)
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} tasks to complete...")
            done, pending = await asyncio.wait(
                self.active_tasks, timeout=30
            )
            if pending:
                logger.warning(f"Cancelling {len(pending)} remaining tasks...")
                for task in pending:
                    task.cancel()

        # 3. ML 학습 작업 체크포인트 저장
        logger.info("Saving ML training checkpoints...")
        await self._save_ml_checkpoints()

        # 4. MLflow 실행 중인 Run 종료
        logger.info("Finalizing MLflow runs...")

        # 5. 텔레그램 봇 정리
        logger.info("Shutting down Telegram bot...")

        # 6. WebSocket 연결 종료
        logger.info("Closing WebSocket connections...")

        # 7. DB 연결 종료
        logger.info("Closing database connections...")

        logger.info("Graceful shutdown complete.")
```
