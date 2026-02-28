# 01. 시스템 아키텍처 상세 설계

## 1. 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 인터페이스                          │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │ Telegram Bot  │    │ Web Dashboard (React + PixiJS)       │   │
│  │  (1차 인터페이스) │    │  - 오피스 시뮬레이션                    │   │
│  │              │    │  - 실시간 대시보드                      │   │
│  └──────┬───────┘    └──────────────┬───────────────────────┘   │
│         │                           │                           │
│         │        WebSocket          │         REST API          │
└─────────┼───────────────────────────┼───────────────────────────┘
          │                           │
┌─────────┼───────────────────────────┼───────────────────────────┐
│         ▼                           ▼                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              API Gateway (FastAPI)                       │    │
│  │  - REST API 라우팅                                       │    │
│  │  - WebSocket 관리                                        │    │
│  │  - 인증/인가 미들웨어                                     │    │
│  │  - Rate Limiting                                         │    │
│  └──────────────────────┬──────────────────────────────────┘    │
│                         │                                       │
│  ┌──────────────────────┼──────────────────────────────────┐    │
│  │          Orchestrator (팀 오케스트레이터)                  │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐     │    │
│  │  │ 수집팀 매니저 │  │ 분석팀 매니저 │  │ 예측팀 매니저     │     │    │
│  │  │ Data Eng   │  │ Data Sci   │  │ ML Eng         │     │    │
│  │  │ Manager    │  │ Manager    │  │ Manager        │     │    │
│  │  └─────┬──────┘  └─────┬──────┘  └───────┬────────┘     │    │
│  │        │               │                  │              │    │
│  │        │               │          ┌───────────────┐      │    │
│  │        │               │          │ 보고서팀 매니저  │      │    │
│  │        │               │          │ Report Manager │      │    │
│  │        │               │          └──────┬────────┘      │    │
│  │        │               │                 │               │    │
│  │   ┌────┴────┐    ┌─────┴─────┐    ┌──────┴──────┐       │    │
│  │   │ Agents  │    │  Agents   │    │   Agents    │       │    │
│  │   │ (수집)   │    │ (DS분석)  │    │(ML예측/보고서)│       │    │
│  │   └────┬────┘    └─────┬─────┘    └──────┬──────┘       │    │
│  └────────┼───────────────┼─────────────────┼──────────────┘    │
│           │               │                 │                   │
│  ┌────────┼───────────────┼─────────────────┼──────────────┐    │
│  │        ▼               ▼                 ▼              │    │
│  │              ML 파이프라인 레이어 (NEW)                    │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │Feature   │ │Model     │ │Experiment│ │Backtest  │   │    │
│  │  │Store     │ │Registry  │ │Tracking  │ │Engine    │   │    │
│  │  │(피처저장) │ │(모델관리) │ │(MLflow)  │ │(백테스팅) │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              데이터 레이어 (Supabase)                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │PostgreSQL│ │ Auth     │ │ Storage  │ │ Realtime │   │    │
│  │  │ (DB)     │ │ (인증)    │ │(모델/차트)│ │ (구독)    │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              외부 서비스 연동                              │    │
│  │  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │    │
│  │  │MCP Server │ │LLM API   │ │Playwright│ │Telegram   │ │    │
│  │  │(도구 관리)  │ │(GPT/Claude)│ │(스크래핑) │ │Bot API    │ │    │
│  │  └───────────┘ └──────────┘ └──────────┘ └───────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         Backend Server                          │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 모듈 구조 (Python 패키지)

```
ai_data_science_team/
├── __init__.py
├── main.py                          # FastAPI 앱 진입점
├── config/
│   ├── __init__.py
│   ├── settings.py                  # 환경변수 기반 설정 (Pydantic Settings)
│   └── constants.py                 # 상수 정의 (섹터, 시장 코드 등)
│
├── api/                             # API 라우터
│   ├── __init__.py
│   ├── router.py                    # 라우터 통합
│   ├── v1/
│   │   ├── stocks.py                # 종목 관련 API
│   │   ├── analyses.py              # 분석 관련 API
│   │   ├── forecasts.py             # 전망 관련 API
│   │   ├── agents.py                # 에이전트 상태 API
│   │   └── ws.py                    # WebSocket 엔드포인트
│   └── deps.py                      # 의존성 주입
│
├── core/                            # 핵심 비즈니스 로직
│   ├── __init__.py
│   ├── orchestrator.py              # 팀 오케스트레이터
│   ├── task_queue.py                # 작업 큐 관리
│   ├── event_bus.py                 # 이벤트 버스 (에이전트 간 통신)
│   └── state_manager.py             # 에이전트 상태 관리 (웹 시각화 연동)
│
├── agents/                          # AI 에이전트
│   ├── __init__.py
│   ├── base.py                      # 기본 에이전트 추상 클래스
│   ├── collection/                  # 수집팀
│   │   ├── __init__.py
│   │   ├── manager.py               # 수집팀 매니저
│   │   ├── stock_collector.py       # 주가 데이터 수집 에이전트
│   │   ├── disclosure_collector.py  # 공시 수집 에이전트
│   │   ├── news_collector.py        # 뉴스 수집 에이전트
│   │   └── scrapers/               # 스크래퍼 구현
│   │       ├── naver_finance.py
│   │       ├── dart.py
│   │       ├── krx.py
│   │       └── news_sources.py
│   ├── analysis/                    # 분석팀
│   │   ├── __init__.py
│   │   ├── manager.py               # 분석팀 매니저
│   │   ├── technical.py             # 기술적 분석 에이전트
│   │   ├── fundamental.py           # 기본적 분석 에이전트
│   │   ├── sentiment.py             # 감성 분석 에이전트 (LLM)
│   │   └── sector.py                # 섹터 분석 에이전트
│   ├── forecast/                    # 전망팀
│   │   ├── __init__.py
│   │   ├── manager.py               # 전망팀 매니저
│   │   ├── short_term.py            # 단기 전망 에이전트
│   │   ├── mid_long_term.py         # 중장기 전망 에이전트
│   │   └── risk_assessor.py         # 리스크 평가 에이전트
│   └── report/                      # 보고서팀 ← NEW
│       ├── __init__.py
│       ├── manager.py               # 보고서팀 매니저
│       ├── comprehensive_reporter.py # 종합 리포터 에이전트
│       ├── investment_memo.py       # 투자 메모 작성 에이전트
│       ├── risk_note.py             # 리스크 노트 작성 에이전트
│       └── report_editor.py         # 편집장 에이전트 (최종 검토/발송)
│
├── mcp/                             # MCP (Model Context Protocol) 서버
│   ├── __init__.py
│   ├── server.py                    # MCP 서버 구현
│   ├── tools/                       # MCP 도구 정의
│   │   ├── browser_tools.py         # Playwright 브라우저 도구
│   │   ├── data_tools.py            # 데이터 처리 도구
│   │   └── analysis_tools.py        # 분석 도구
│   └── resources/                   # MCP 리소스
│       └── stock_data.py
│
├── telegram/                        # 텔레그램 봇
│   ├── __init__.py
│   ├── bot.py                       # 봇 메인 로직
│   ├── handlers/                    # 커맨드 핸들러
│   │   ├── collect.py               # /수집 핸들러
│   │   ├── analyze.py               # /분석 핸들러
│   │   ├── forecast.py              # /전망 핸들러
│   │   └── report.py                # /리포트 핸들러
│   ├── formatters/                  # 메시지 포맷터
│   │   ├── stock_formatter.py
│   │   └── report_formatter.py
│   └── middleware.py                # 인증, 로깅 미들웨어
│
├── db/                              # 데이터베이스
│   ├── __init__.py
│   ├── supabase_client.py           # Supabase 클라이언트
│   ├── models.py                    # SQLAlchemy/Pydantic 모델
│   ├── repositories/               # 리포지토리 패턴
│   │   ├── stock_repo.py
│   │   ├── analysis_repo.py
│   │   └── forecast_repo.py
│   └── migrations/                  # DB 마이그레이션
│
├── llm/                             # LLM 연동
│   ├── __init__.py
│   ├── client.py                    # LLM 클라이언트 (다중 프로바이더)
│   ├── prompts/                     # 프롬프트 템플릿
│   │   ├── sentiment.py
│   │   ├── summary.py
│   │   ├── forecast.py
│   │   └── report.py
│   └── chains.py                    # LLM 체인 구성
│
├── security/                        # 보안
│   ├── __init__.py
│   ├── auth.py                      # 인증 모듈
│   ├── api_key_manager.py           # API 키 암호화 관리
│   └── rate_limiter.py              # Rate limiting
│
└── utils/                           # 유틸리티
    ├── __init__.py
    ├── logger.py                    # 구조화된 로깅
    ├── validators.py                # 데이터 검증
    └── formatters.py                # 데이터 포맷팅
```

## 3. 데이터 흐름 (Data Flow)

### 3.1 요청 → 수집 → 분석 → 전망 파이프라인

```
[텔레그램 요청]
      │
      ▼
[Orchestrator] ─── 작업 생성 ──→ [Task Queue]
      │                              │
      │                              ▼
      │                    [수집팀 매니저]
      │                    ├── stock_collector (MCP → Playwright → 네이버금융)
      │                    ├── disclosure_collector (MCP → Playwright → DART)
      │                    └── news_collector (MCP → Playwright → 뉴스)
      │                              │
      │                    수집 완료 이벤트
      │                              │
      │                              ▼
      │                    [분석팀 매니저]
      │                    ├── technical (pandas-ta → 기술적 지표)
      │                    ├── fundamental (재무제표 분석)
      │                    ├── sentiment (LLM → 뉴스/공시 감성)
      │                    └── sector (섹터 상관관계)
      │                              │
      │                    분석 완료 이벤트
      │                              │
      │                              ▼
      │                    [전망팀 매니저]
      │                    ├── short_term (1주 전망)
      │                    ├── mid_long_term (1~3개월)
      │                    └── risk_assessor (리스크 평가)
      │                              │
      │                    전망 완료 이벤트
      │                              │
      │                              ▼
      │                    [보고서팀 매니저] ← NEW
      │                    ├── comprehensive_reporter (종합 리포트)
      │                    ├── investment_memo (투자 메모)
      │                    ├── risk_note (리스크 노트)
      │                    └── report_editor (편집장: 최종 검토 & 발송)
      │                              │
      │                    보고서 완료 이벤트
      │                              │
      ▼                              ▼
[텔레그램 응답]              [웹 대시보드 업데이트]
```

### 3.2 이벤트 기반 상태 관리

```python
# 이벤트 타입 정의
class EventType(Enum):
    # 수집 이벤트
    COLLECTION_STARTED = "collection.started"
    COLLECTION_PROGRESS = "collection.progress"
    COLLECTION_COMPLETED = "collection.completed"
    COLLECTION_FAILED = "collection.failed"

    # 분석 이벤트
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_PROGRESS = "analysis.progress"
    ANALYSIS_COMPLETED = "analysis.completed"

    # 전망 이벤트
    FORECAST_STARTED = "forecast.started"
    FORECAST_COMPLETED = "forecast.completed"

    # 보고서 이벤트 ← NEW
    REPORT_STARTED = "report.started"
    REPORT_PROGRESS = "report.progress"
    REPORT_REVIEW = "report.review"        # 편집장 검토 시작
    REPORT_APPROVED = "report.approved"    # 편집장 승인
    REPORT_COMPLETED = "report.completed"  # 최종 발송 완료

    # 에이전트 이벤트
    AGENT_STATE_CHANGED = "agent.state_changed"
    AGENT_TASK_ASSIGNED = "agent.task_assigned"
```

## 4. 통신 프로토콜

### 4.1 WebSocket 메시지 포맷

```json
{
  "type": "agent_state_update",
  "payload": {
    "team": "collection",
    "agent_id": "kospi_collector_01",
    "agent_name": "KOSPI 반도체 수집기",
    "status": "working",
    "current_task": "삼성전자 주가 수집 중",
    "progress": 0.65,
    "animation_state": "collecting"
  },
  "timestamp": "2026-02-28T10:30:00Z"
}
```

### 4.2 에이전트 애니메이션 상태 맵핑

```
Agent Status    →  Animation State  →  PixiJS 렌더링
─────────────────────────────────────────────────────
idle            →  sitting          →  캐릭터 앉아있음
working         →  collecting       →  타이핑 + 파티클 효과
working         →  analyzing        →  차트 보는 모션
working         →  writing          →  문서 작성 모션
working         →  reviewing        →  보고서 검토/편집 모션
working         →  summarizing      →  종합 요약 작성 모션
transferring    →  delivering       →  서류 배달 캐릭터 이동
completed       →  celebrating      →  ✓ 체크 이펙트
failed          →  troubled         →  ❗ 에러 이펙트
```

## 5. MCP (Model Context Protocol) 아키텍처

```
┌──────────────────────────────────────────┐
│           MCP Server                      │
│  ┌────────────────────────────────────┐   │
│  │ Tools                              │   │
│  │  ├── browse_stock_page             │   │
│  │  │   (Playwright로 주가 페이지 탐색)  │   │
│  │  ├── extract_price_data            │   │
│  │  │   (가격 데이터 추출)              │   │
│  │  ├── search_disclosure             │   │
│  │  │   (DART 공시 검색)               │   │
│  │  ├── search_news                   │   │
│  │  │   (뉴스 검색)                    │   │
│  │  ├── calculate_indicators          │   │
│  │  │   (기술적 지표 계산)              │   │
│  │  └── generate_chart                │   │
│  │      (차트 이미지 생성)              │   │
│  └────────────────────────────────────┘   │
│  ┌────────────────────────────────────┐   │
│  │ Resources                          │   │
│  │  ├── stock://005930/price          │   │
│  │  ├── stock://005930/disclosure     │   │
│  │  └── stock://005930/analysis       │   │
│  └────────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

## 6. 확장성 설계

### 6.1 플러그인 구조
새로운 데이터 소스나 분석 모델을 쉽게 추가할 수 있는 플러그인 패턴:

```python
# agents/base.py
class BaseAgent(ABC):
    """모든 에이전트의 기본 클래스"""

    def __init__(self, agent_id: str, name: str, team: str):
        self.agent_id = agent_id
        self.name = name
        self.team = team
        self.status: AgentStatus = AgentStatus.IDLE
        self.current_task: Optional[str] = None

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """작업 실행"""
        pass

    async def update_status(self, status: AgentStatus, task_desc: str = ""):
        """상태 업데이트 → 이벤트 버스로 전파 → 웹 시각화 반영"""
        self.status = status
        self.current_task = task_desc
        await event_bus.emit(EventType.AGENT_STATE_CHANGED, {
            "agent_id": self.agent_id,
            "status": status.value,
            "task": task_desc
        })
```

### 6.2 데이터 소스 레지스트리
```python
# 새 데이터 소스 추가 시 데코레이터 기반 등록
@register_scraper("yahoo_finance")
class YahooFinanceScraper(BaseScraper):
    async def scrape(self, stock_code: str) -> StockData:
        ...
```

## 7. 에러 핸들링 전략

```
Layer           │ 전략
────────────────┼──────────────────────────────────
스크래핑        │ 재시도 3회 + 대체 소스 자동 전환
LLM API        │ 폴백 모델 (GPT-4 → GPT-3.5 → 로컬)
DB             │ 연결 풀 + 지수 백오프 재시도
WebSocket      │ 자동 재연결 + 폴링 폴백
텔레그램        │ 큐 기반 전송 + Rate limit 준수
전체 파이프라인  │ 부분 실패 허용 (수집 일부 실패해도 분석 진행)
```
