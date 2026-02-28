# 06. 웹 시각화 상세 설계

## 1. 개요

Claw-Empire를 벤치마킹한 PixiJS 기반 오피스 시뮬레이션으로, AI 금융 데이터사이언스 팀의 작업 과정(데이터 수집, EDA, 피처 엔지니어링, ML 모델 학습, 백테스팅)을 실시간 캐릭터 애니메이션으로 시각화합니다.

## 2. 프론트엔드 프로젝트 구조

```
web/
├── src/
│   ├── main.tsx                     # React 진입점
│   ├── App.tsx                      # 메인 레이아웃
│   │
│   ├── components/
│   │   ├── office-view/             # PixiJS 오피스 시뮬레이션
│   │   │   ├── OfficeCanvas.tsx     # PixiJS Canvas 래퍼
│   │   │   ├── buildScene.ts        # 씬 구성
│   │   │   ├── buildTeamRooms.ts    # 팀별 방 구성
│   │   │   ├── officeTicker.ts      # 애니메이션 루프
│   │   │   ├── characters.ts        # 캐릭터 스프라이트 관리
│   │   │   ├── particles.ts         # 파티클 효과
│   │   │   ├── delivery.ts          # 서류 배달 애니메이션
│   │   │   ├── themes.ts            # 테마 & 색상
│   │   │   └── model.ts             # 상수 & 타입
│   │   │
│   │   ├── dashboard/               # 금융 데이터사이언스 대시보드
│   │   │   ├── MarketOverview.tsx    # 시장 개요 (KOSPI/KOSDAQ)
│   │   │   ├── StockCard.tsx        # 종목 카드
│   │   │   ├── PriceChart.tsx       # 주가 차트
│   │   │   ├── EDAPanel.tsx         # EDA 결과 패널 (분포, 정상성, 이상치)
│   │   │   ├── FeaturePanel.tsx     # 피처 중요도 차트
│   │   │   ├── MLModelPanel.tsx     # ML 모델 성능 비교 패널
│   │   │   ├── BacktestPanel.tsx    # 백테스트 결과 패널
│   │   │   ├── ExperimentLog.tsx    # MLflow 실험 추적 로그
│   │   │   ├── ReportPanel.tsx      # 보고서 작성 현황 패널
│   │   │   ├── TeamStatus.tsx       # 팀 상태 패널
│   │   │   └── ActivityLog.tsx      # 활동 로그
│   │   │
│   │   ├── chat-panel/              # 채팅 패널 (텔레그램 미러)
│   │   │   ├── ChatPanel.tsx
│   │   │   └── MessageBubble.tsx
│   │   │
│   │   ├── ml-view/                 # ML 시각화 컴포넌트
│   │   │   ├── TrainingProgress.tsx  # 모델 학습 진행률 (Epoch/Trial)
│   │   │   ├── LossChart.tsx        # 실시간 Loss 곡선
│   │   │   ├── ConfusionMatrix.tsx  # 방향 예측 혼동 행렬
│   │   │   ├── PredictionChart.tsx  # 예측 vs 실제 차트
│   │   │   └── RiskGauge.tsx        # VaR/CVaR 게이지
│   │   │
│   │   └── common/                  # 공통 컴포넌트
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── LoadingSpinner.tsx
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts          # WebSocket 연결
│   │   ├── useAgentState.ts         # 에이전트 상태 구독
│   │   └── useMarketData.ts         # 시장 데이터
│   │
│   ├── types/
│   │   └── index.ts                 # 타입 정의
│   │
│   └── api/
│       └── client.ts                # API 클라이언트
│
├── public/
│   └── assets/
│       ├── sprites/                 # 캐릭터 스프라이트 시트
│       │   ├── collector.png        # 수집팀 캐릭터
│       │   ├── eda_analyst.png      # EDA/통계 분석 캐릭터
│       │   ├── feature_engineer.png # 피처 엔지니어 캐릭터
│       │   ├── ml_engineer.png      # ML 엔지니어 캐릭터
│       │   ├── backtester.png       # 백테스터 캐릭터
│       │   ├── report_writer.png   # 종합 리포터 캐릭터
│       │   ├── invest_memo.png     # 투자 메모 작성자 캐릭터
│       │   ├── risk_note.png       # 리스크 노트 작성자 캐릭터
│       │   ├── report_editor.png   # 편집장(총괄) 캐릭터
│       │   └── delivery.png         # 배달 캐릭터
│       ├── furniture/               # 가구 & 소품
│       │   ├── desk.png
│       │   ├── computer.png
│       │   ├── chart_screen.png
│       │   ├── gpu_server.png       # ML 학습 서버 소품
│       │   └── whiteboard.png       # 통계 수식 화이트보드
│       └── ui/                      # UI 아이콘
│
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.ts
```

## 3. 오피스 레이아웃

### 3.1 전체 구조

```
┌──────────────────────────────────────────────────────────────┐
│                     Header (시장 현황 바)                      │
│  KOSPI 2,850.34 (+0.52%)  │  KOSDAQ 912.45 (-0.31%)         │
├────────────────────┬───────────────────────────┬─────────────┤
│                    │                           │             │
│  ┌──────────────┐  │  ┌─────────────────────┐  │  Dashboard  │
│  │  수집팀 방     │  │  │   복도 / 전달 통로    │  │  (사이드바)  │
│  │  Collection   │  │  │                     │  │             │
│  │  Team Room    │  │  │   서류 배달 캐릭터     │  │  탭 전환:    │
│  │              │  │  │   이동 경로           │  │  • 시장 개요  │
│  │  🧑‍💻🧑‍💻🧑‍💻     │  │  │                     │  │  • EDA 결과  │
│  │  🧑‍💻🧑‍💻       │  │  │   📄→ →→ →→         │  │  • 피처 분석  │
│  └──────────────┘  │  │                     │  │  • ML 모델   │
│                    │  └─────────────────────┘  │  • 백테스트  │
│  ┌──────────────┐  │                           │  • 실험 로그  │
│  │  분석팀 방     │  │  ┌─────────────────────┐  │  • 활동 로그  │
│  │  Data Science │  │  │   ML 학습 현황 패널   │  │  • 팀 상태   │
│  │  Team Room    │  │  │                     │  │             │
│  │              │  │  │  Model    Epoch  Loss│  │             │
│  │  📊📊📊       │  │  │  Prophet  ✅ Done    │  │             │
│  │  🔧🔧📈       │  │  │  LSTM     35/50 0.02│  │             │
│  └──────────────┘  │  │  XGBoost  Trial 12  │  │             │
│                    │  │                     │  │             │
│  ┌──────────────┐  │  └─────────────────────┘  │             │
│  │  ML팀 방      │  │                           │             │
│  │  ML Eng.      │  │                           │             │
│  │  Team Room    │  │                           │             │
│  │              │  │                           │             │
│  │  🤖🤖🤖       │  │                           │             │
│  │  🧪⚠️         │  │                           │             │
│  └──────────────┘  │                           │             │
│                    │  ┌─────────────────────┐  │             │
│  ┌──────────────┐  │  │   보고서 작성 현황      │  │  • 보고서   │
│  │  보고서팀 방   │  │  │                     │  │             │
│  │  Report       │  │  │  종합리포트  ████░ 75%│  │             │
│  │  Team Room    │  │  │  투자메모   ✅ Done   │  │             │
│  │              │  │  │  리스크노트  대기중    │  │             │
│  │  📝📊📋       │  │  │                     │  │             │
│  │  🧑‍💼          │  │  └─────────────────────┘  │             │
│  └──────────────┘  │                           │             │
│                    │                           │             │
├────────────────────┴───────────────────────────┴─────────────┤
│  Footer (상태 바, 텔레그램 연결, MLflow 상태, GPU 사용률)        │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 팀 방 내부 레이아웃

```
수집팀 방 (Collection Team Room)
┌─────────────────────────────────┐
│  [수집팀] Collection Team        │
│                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐       │
│  │ 🖥️  │ │ 🖥️  │ │ 🖥️  │       │
│  │ 🧑‍💻  │ │ 🧑‍💻  │ │ 🧑‍💻  │       │  ← KOSPI 수집기 3개
│  │KOSPI │ │KOSPI │ │KOSPI │       │
│  │반도체 │ │자동차 │ │바이오 │       │
│  └─────┘ └─────┘ └─────┘       │
│                                 │
│  ┌─────┐ ┌─────┐               │
│  │ 📰  │ │ 📋  │               │
│  │ 🧑‍💻  │ │ 🧑‍💻  │               │  ← 뉴스, 공시 수집기
│  │ 뉴스  │ │ 공시  │               │
│  └─────┘ └─────┘               │
│                                 │
│  상태: 수집 중... ████░░ 65%     │
└─────────────────────────────────┘

분석팀 방 (Data Science Team Room)
┌─────────────────────────────────┐
│  [분석팀] Data Science Team      │
│                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐       │
│  │ 📊  │ │ 🔧  │ │ 📈  │       │
│  │ 🧑‍💻  │ │ 🧑‍💻  │ │ 🧑‍💻  │       │
│  │ EDA  │ │피처  │ │통계  │       │  ← EDA, 피처 엔지니어링, 통계 분석
│  │분석가 │ │엔지니어│ │분석가 │       │
│  └─────┘ └─────┘ └─────┘       │
│                                 │
│  ┌─────┐ ┌─────┐               │
│  │ 💬  │ │ 🏢  │               │
│  │ 🧑‍💻  │ │ 🧑‍💻  │               │  ← 감성 분석, 섹터 분석
│  │ 감성  │ │ 섹터  │               │
│  │NLP   │ │클러스터│               │
│  └─────┘ └─────┘               │
│                                 │
│  [화이트보드] ADF p=0.02 ✅      │
│  상태: 피처 엔지니어링 중 █████░ 80% │
└─────────────────────────────────┘

ML팀 방 (ML Engineering Team Room)
┌─────────────────────────────────┐
│  [ML팀] ML Engineering Team      │
│                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐       │
│  │ 🤖  │ │ 🧪  │ │ ⚠️  │       │
│  │ 🧑‍💻  │ │ 🧑‍💻  │ │ 🧑‍💻  │       │
│  │모델  │ │백테스트│ │리스크 │       │  ← 모델 학습, 백테스팅, 리스크
│  │트레이너│ │    │ │평가  │       │
│  └─────┘ └─────┘ └─────┘       │
│                                 │
│          [GPU 서버 랙]           │
│           ┌──────────────┐     │
│           │ LSTM Epoch 35 │     │  ← GPU 서버
│           │ Loss: 0.0231  │     │
│           └──────────────┘     │
│                                 │
│  상태: XGBoost 학습 중 Trial 12/30 │
└─────────────────────────────────┘

보고서팀 방 (Report Team Room)
┌─────────────────────────────────┐
│  [보고서팀] Report Team           │
│                                 │
│  ┌─────┐ ┌─────┐ ┌─────┐       │
│  │ 📝  │ │ 📊  │ │ 📋  │       │
│  │ 🧑‍💼  │ │ 🧑‍💼  │ │ 🧑‍💼  │       │
│  │종합  │ │투자  │ │리스크 │       │  ← 종합 리포트, 투자 메모, 리스크 노트
│  │리포터 │ │메모  │ │노트  │       │
│  └─────┘ └─────┘ └─────┘       │
│                                 │
│  ┌─────┐                       │
│  │ 🧑‍💼  │ [보고서 출력 패널]      │
│  │편집장 │  ┌──────────────┐     │  ← 종합 편집 + 텔레그램 전송
│  │(총괄) │  │ 최종 보고서     │     │
│  └─────┘  │ 전송 대기중...  │     │
│           └──────────────┘     │
│                                 │
│  상태: 종합 리포트 작성 중 ████░ 75% │
└─────────────────────────────────┘
```

## 4. 캐릭터 애니메이션 시스템

### 4.1 캐릭터 상태 머신

```typescript
// office-view/model.ts

export enum CharacterState {
  IDLE = "idle",                    // 앉아서 대기
  WORKING = "working",             // 작업 중 (타이핑/분석)
  COLLECTING = "collecting",       // 데이터 수집 중
  EDA = "eda",                     // 탐색적 데이터 분석 중
  FEATURE_ENGINEERING = "feature_engineering", // 피처 엔지니어링 중
  ANALYZING = "analyzing",         // 통계 분석 중
  SENTIMENT = "sentiment",         // 감성 분석 중 (TF-IDF + LLM)
  CLUSTERING = "clustering",       // 섹터 클러스터링 중
  TRAINING = "training",           // ML 모델 학습 중
  OPTIMIZING = "optimizing",       // 하이퍼파라미터 최적화 중 (Optuna)
  BACKTESTING = "backtesting",     // 백테스팅 수행 중
  RISK_ASSESSING = "risk_assessing", // 리스크 평가 중 (VaR/Monte Carlo)
  WRITING = "writing",             // 리포트 작성 중
  REVIEWING = "reviewing",         // 보고서 검토/편집 중
  SUMMARIZING = "summarizing",     // 종합 요약 작성 중
  DELIVERING = "delivering",       // 서류 배달 중
  CELEBRATING = "celebrating",     // 작업 완료
  ERROR = "error",                 // 에러 발생
}

export interface AgentVisual {
  id: string;
  name: string;
  role: string;                    // "eda_analyst" | "feature_engineer" | "model_trainer" 등
  team: "collection" | "analysis" | "ml_engineering" | "report";
  state: CharacterState;
  position: { x: number; y: number };
  sprite: PIXI.AnimatedSprite;
  desk: PIXI.Container;
  particles: ParticleEmitter;
  statusBubble: PIXI.Text;
  progressBar: PIXI.Graphics;
  mlMetrics?: {                    // ML 학습 중 실시간 메트릭
    epoch?: number;
    totalEpochs?: number;
    loss?: number;
    trial?: number;
    totalTrials?: number;
    modelName?: string;
  };
}

// 애니메이션 상수
export const ANIMATION_CONFIG = {
  TYPING_SPEED: 0.15,              // 타이핑 프레임 속도
  PARTICLE_INTERVAL: 8,            // 파티클 생성 간격 (틱)
  DELIVERY_SPEED: 0.015,           // 배달 캐릭터 이동 속도
  CELEBRATION_DURATION: 60,        // 축하 애니메이션 틱 수
  PROGRESS_BAR_WIDTH: 80,          // 진행 바 너비
  STATUS_BUBBLE_OFFSET_Y: -30,     // 상태 말풍선 Y 오프셋
};
```

### 4.2 애니메이션 루프

```typescript
// office-view/officeTicker.ts

export function createOfficeTicker(state: OfficeState) {
  let tick = 0;

  return (delta: number) => {
    tick++;

    // 각 에이전트 애니메이션 업데이트
    for (const agent of state.agents) {
      updateAgentAnimation(agent, tick);
    }

    // 배달 캐릭터 업데이트
    for (const delivery of state.deliveries) {
      updateDelivery(delivery, tick);
    }

    // 파티클 업데이트
    updateParticles(state.particles, tick);

    // 시장 데이터 티커 업데이트
    updateMarketTicker(state.marketTicker, tick);
  };
}

function updateAgentAnimation(agent: AgentVisual, tick: number) {
  switch (agent.state) {
    case CharacterState.IDLE:
      // 미세한 호흡 애니메이션 (상하 진동)
      agent.sprite.y = agent.position.y + Math.sin(tick * 0.03) * 1;
      break;

    case CharacterState.COLLECTING:
      // 타이핑 모션 + 데이터 파티클 (위에서 아래로)
      if (tick % 8 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % ANIMATION_CONFIG.PARTICLE_INTERVAL === 0) {
        emitDataParticle(agent, "collecting"); // 초록색 데이터 파티클
      }
      break;

    case CharacterState.EDA:
      // 차트/히스토그램 파티클 (데이터 분포 시각화)
      if (tick % 10 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 12 === 0) {
        emitDataParticle(agent, "eda"); // 히스토그램 파티클
      }
      break;

    case CharacterState.FEATURE_ENGINEERING:
      // 기어/톱니 회전 모션 + 피처 생성 파티클
      if (tick % 8 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 10 === 0) {
        emitDataParticle(agent, "feature_engineering"); // 기어 파티클
      }
      break;

    case CharacterState.ANALYZING:
      // 수식/통계 파티클 (p-value, 회귀선)
      if (tick % 12 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 15 === 0) {
        emitDataParticle(agent, "analyzing"); // 파란색 수식 파티클
      }
      break;

    case CharacterState.TRAINING:
      // 신경망 학습 모션 + Loss 감소 파티클 (위에서 아래로 줄어듦)
      if (tick % 6 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 8 === 0) {
        emitDataParticle(agent, "training"); // 뉴런 연결 파티클
      }
      // GPU 서버 랙 LED 깜박임 효과
      if (agent.desk) {
        updateGPUServerLEDs(agent.desk, tick);
      }
      break;

    case CharacterState.OPTIMIZING:
      // Optuna Trial 진행 모션 + 탐색 파티클 (다방향 산개)
      if (tick % 5 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 10 === 0) {
        emitDataParticle(agent, "optimizing"); // 탐색 포인트 파티클
      }
      break;

    case CharacterState.BACKTESTING:
      // 차트 스크롤 모션 + 매수/매도 시그널 파티클
      if (tick % 8 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 12 === 0) {
        emitDataParticle(agent, "backtesting"); // 매수(초록)/매도(빨강) 파티클
      }
      break;

    case CharacterState.RISK_ASSESSING:
      // 경고 게이지 모션 + 리스크 파티클
      if (tick % 10 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 15 === 0) {
        emitDataParticle(agent, "risk"); // 경고 삼각형 파티클
      }
      break;

    case CharacterState.WRITING:
      // 문서 작성 모션 + 글자 파티클
      if (tick % 6 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 20 === 0) {
        emitTextParticle(agent); // 텍스트 파티클
      }
      break;

    case CharacterState.REVIEWING:
      // 문서 검토 모션 + 체크/수정 파티클
      if (tick % 10 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 18 === 0) {
        emitDataParticle(agent, "reviewing"); // 체크마크/펜 파티클
      }
      break;

    case CharacterState.SUMMARIZING:
      // 종합 요약 모션 + 여러 문서가 하나로 합쳐지는 파티클
      if (tick % 7 === 0) {
        agent.sprite.currentFrame =
          (agent.sprite.currentFrame + 1) % agent.sprite.totalFrames;
      }
      if (tick % 12 === 0) {
        emitDataParticle(agent, "summarizing"); // 문서 수렴 파티클
      }
      break;

    case CharacterState.CELEBRATING:
      // 체크마크 이펙트 + 반짝 파티클
      if (tick % 5 === 0) {
        emitCelebrationParticle(agent);
      }
      break;

    case CharacterState.ERROR:
      // 빨간 느낌표 + 흔들림
      agent.sprite.x = agent.position.x + Math.sin(tick * 0.5) * 2;
      break;
  }

  // 진행 바 업데이트
  if (agent.progressBar && agent.progress !== undefined) {
    updateProgressBar(agent.progressBar, agent.progress);
  }

  // 상태 말풍선 업데이트
  if (agent.statusBubble && agent.statusText) {
    agent.statusBubble.text = agent.statusText;
  }
}
```

### 4.3 서류 배달 애니메이션

```typescript
// office-view/delivery.ts

interface Delivery {
  id: string;
  sprite: PIXI.Sprite;
  from: { x: number; y: number };  // 출발 팀 위치
  to: { x: number; y: number };    // 도착 팀 위치
  progress: number;                 // 0~1
  documentSprite: PIXI.Sprite;     // 서류 이미지
}

export function createDelivery(
  from: TeamRoom,
  to: TeamRoom,
  documentType: string
): Delivery {
  // 배달 캐릭터 생성
  const sprite = new PIXI.Sprite(deliveryTexture);
  sprite.anchor.set(0.5);

  // 서류 스프라이트
  const docSprite = new PIXI.Sprite(documentTextures[documentType]);

  return {
    id: crypto.randomUUID(),
    sprite,
    from: from.exitPoint,
    to: to.entryPoint,
    progress: 0,
    documentSprite: docSprite,
  };
}

export function updateDelivery(delivery: Delivery, tick: number) {
  delivery.progress += ANIMATION_CONFIG.DELIVERY_SPEED;

  if (delivery.progress >= 1) {
    // 도착 → 전달 이펙트
    emitDeliveryCompleteEffect(delivery.to);
    return true; // 제거 플래그
  }

  // 베지어 곡선 경로로 이동
  const { x, y } = getBezierPoint(
    delivery.from,
    { x: (delivery.from.x + delivery.to.x) / 2, y: delivery.from.y - 50 },
    delivery.to,
    delivery.progress
  );

  delivery.sprite.x = x;
  delivery.sprite.y = y;

  // 서류가 위아래로 살짝 흔들림
  delivery.documentSprite.y = y - 15 + Math.sin(tick * 0.1) * 3;
  delivery.documentSprite.x = x + 10;

  return false;
}
```

### 4.4 파티클 효과

```typescript
// office-view/particles.ts

interface Particle {
  sprite: PIXI.Sprite;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  type: "data" | "chart" | "text" | "celebration" | "error";
}

const PARTICLE_CONFIGS = {
  collecting: {
    color: 0x4CAF50,     // 초록색
    shape: "circle",
    count: 3,
    speed: 1.5,
    direction: "up",
    icon: "📊",
  },
  eda: {
    color: 0x00BCD4,     // 시안색
    shape: "histogram",
    count: 2,
    speed: 1.0,
    direction: "up",
    icon: "📊",
  },
  feature_engineering: {
    color: 0x795548,     // 갈색
    shape: "gear",
    count: 2,
    speed: 0.8,
    direction: "circular",
    icon: "🔧",
  },
  analyzing: {
    color: 0x2196F3,     // 파란색
    shape: "formula",
    count: 2,
    speed: 1.0,
    direction: "circular",
    icon: "📈",
  },
  training: {
    color: 0xE91E63,     // 핑크색
    shape: "neuron",
    count: 4,
    speed: 1.2,
    direction: "converge",  // 중심으로 수렴
    icon: "🤖",
  },
  optimizing: {
    color: 0xFF5722,     // 딥오렌지색
    shape: "diamond",
    count: 3,
    speed: 1.5,
    direction: "scatter",   // 다방향 산개
    icon: "🎯",
  },
  backtesting: {
    color: 0x4CAF50,     // 초록색 (매수) + 0xF44336 (매도)
    shape: "arrow",
    count: 2,
    speed: 1.0,
    direction: "horizontal",
    icon: "🧪",
  },
  risk: {
    color: 0xFF9800,     // 주황색
    shape: "triangle",
    count: 1,
    speed: 0.5,
    direction: "pulse",
    icon: "⚠️",
  },
  writing: {
    color: 0xFF9800,     // 주황색
    shape: "text",
    count: 1,
    speed: 0.5,
    direction: "up",
    icon: "📝",
  },
  reviewing: {
    color: 0x4A148C,     // 진보라색
    shape: "checkmark",
    count: 2,
    speed: 0.8,
    direction: "up",
    icon: "✏️",
  },
  summarizing: {
    color: 0x6A1B9A,     // 보라색
    shape: "document",
    count: 3,
    speed: 1.0,
    direction: "converge",  // 여러 문서가 중심으로 수렴
    icon: "📑",
  },
  celebration: {
    color: 0xFFD700,     // 금색
    shape: "star",
    count: 5,
    speed: 2.0,
    direction: "burst",
    icon: "✨",
  },
  error: {
    color: 0xF44336,     // 빨간색
    shape: "exclamation",
    count: 1,
    speed: 0.5,
    direction: "shake",
    icon: "❗",
  },
};
```

## 5. 실시간 WebSocket 연동

### 5.1 메시지 프로토콜

```typescript
// hooks/useWebSocket.ts

interface WSMessage {
  type: "agent_state" | "delivery" | "market_data" | "task_progress" | "ml_metrics" | "experiment_update" | "notification";
  payload: any;
  timestamp: string;
}

// 에이전트 상태 업데이트
interface AgentStateMessage {
  type: "agent_state";
  payload: {
    agent_id: string;
    role: string;              // "eda_analyst" | "feature_engineer" | "model_trainer" 등
    team: "collection" | "analysis" | "ml_engineering" | "report";
    state: CharacterState;
    status_text: string;
    progress?: number;         // 0~1
    current_stock?: string;    // 현재 처리 중인 종목
  };
}

// ML 학습 메트릭 실시간 업데이트
interface MLMetricsMessage {
  type: "ml_metrics";
  payload: {
    agent_id: string;
    model_name: string;        // "Prophet" | "LSTM" | "XGBoost" | "LightGBM"
    epoch?: number;
    total_epochs?: number;
    trial?: number;
    total_trials?: number;
    loss?: number;
    val_loss?: number;
    metrics?: {
      mape?: number;
      rmse?: number;
      direction_accuracy?: number;
    };
    status: "training" | "optimizing" | "evaluating" | "completed";
  };
}

// MLflow 실험 업데이트
interface ExperimentUpdateMessage {
  type: "experiment_update";
  payload: {
    experiment_id: string;
    run_id: string;
    model_name: string;
    stock_code: string;
    metrics: Record<string, number>;
    status: "running" | "completed" | "failed";
  };
}

// 팀 간 전달 이벤트
interface DeliveryMessage {
  type: "delivery";
  payload: {
    from_team: string;
    to_team: string;
    document_type: "raw_data" | "eda_report" | "features" | "ml_predictions" | "backtest_results" | "risk_report" | "comprehensive_report" | "investment_memo" | "risk_note" | "final_report";
    stock_code: string;
  };
}

// 시장 데이터 업데이트
interface MarketDataMessage {
  type: "market_data";
  payload: {
    kospi: { value: number; change: number };
    kosdaq: { value: number; change: number };
    updated_at: string;
  };
}
```

### 5.2 WebSocket Hook

```typescript
export function useWebSocket(url: string) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const handlers = useRef(new Map<string, Set<(data: any) => void>>());

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // 자동 재연결 (3초 후)
      setTimeout(() => reconnect(), 3000);
    };

    ws.onmessage = (event) => {
      const message: WSMessage = JSON.parse(event.data);
      const typeHandlers = handlers.current.get(message.type);
      if (typeHandlers) {
        typeHandlers.forEach((handler) => handler(message.payload));
      }
    };

    return () => ws.close();
  }, [url]);

  const subscribe = useCallback((type: string, handler: (data: any) => void) => {
    if (!handlers.current.has(type)) {
      handlers.current.set(type, new Set());
    }
    handlers.current.get(type)!.add(handler);

    return () => {
      handlers.current.get(type)?.delete(handler);
    };
  }, []);

  return { connected, subscribe };
}
```

## 6. 대시보드 구성요소

### 6.1 시장 개요 패널

```typescript
// dashboard/MarketOverview.tsx

interface MarketOverviewProps {
  kospi: { value: number; change: number; changeRate: number };
  kosdaq: { value: number; change: number; changeRate: number };
}

// 표시 항목:
// - KOSPI/KOSDAQ 현재지수 + 등락률
// - 거래량/거래대금
// - 상한가/하한가 종목 수
// - 외국인 순매수 금액
```

### 6.2 EDA 결과 패널

```typescript
// dashboard/EDAPanel.tsx

// EDA 결과를 인터랙티브하게 시각화
// - 기술 통계량 테이블 (평균, 중앙값, 표준편차, 왜도, 첨도)
// - 수익률 분포 히스토그램 + 정규분포 오버레이
// - Q-Q Plot (정규성 시각 검정)
// - STL 시계열 분해 차트 (Trend, Seasonal, Residual)
// - ACF/PACF 상관관계 차트
// - 이상치 탐지 결과 (Isolation Forest 시각화)
// - 정상성 검정 결과 뱃지 (ADF: ✅ 정상 / ❌ 비정상)
```

### 6.3 ML 모델 패널

```typescript
// dashboard/MLModelPanel.tsx

// ML 모델 학습 및 성능을 실시간으로 표시
// - 모델별 학습 진행률 (Prophet ✅, LSTM 35/50, XGBoost Trial 12/30)
// - 실시간 Loss 곡선 차트 (train_loss, val_loss)
// - 모델 성능 비교 레이더 차트 (MAPE, RMSE, R², 방향정확도)
// - 앙상블 가중치 파이 차트
// - 예측 vs 실제 라인 차트 (with 신뢰구간)
// - MLflow 실험 ID 링크
```

### 6.4 백테스트 결과 패널

```typescript
// dashboard/BacktestPanel.tsx

// 백테스트 결과를 인터랙티브하게 시각화
// - 누적 수익률 차트 (전략 vs Buy & Hold)
// - Drawdown 차트
// - 매수/매도 시그널 오버레이 차트
// - 성과 메트릭 카드 (Sharpe, Sortino, MDD, 승률, Calmar)
// - Walk-Forward 분할별 성과 비교 바 차트
// - Monte Carlo 시뮬레이션 Fan 차트 (VaR/CVaR 밴드)
```

### 6.5 보고서 현황 패널

```typescript
// dashboard/ReportPanel.tsx

// 보고서팀의 작업 현황을 실시간으로 표시
// - 보고서 유형별 작성 진행률 (종합리포트, 투자메모, 리스크노트)
// - 현재 종합 중인 입력 소스 (수집 데이터 ✅, EDA ✅, 피처 ✅, ML 예측 ✅, 백테스트 ⏳)
// - 편집장 검토 상태 (대기 / 검토중 / 승인 / 반려)
// - 최종 보고서 미리보기 (요약 텍스트)
// - 텔레그램 전송 상태 (대기 / 전송중 / 전송완료)
// - 보고서 히스토리 (과거 발송된 보고서 목록)
```

### 6.6 팀 상태 패널

```typescript
// dashboard/TeamStatus.tsx

// 각 팀의 현재 상태를 실시간으로 표시
// - 팀 이름 + 상태 (대기/작업중/완료)
// - 각 에이전트 상태와 역할
//   - 수집팀: 주가수집기, 공시수집기, 뉴스수집기
//   - 분석팀: EDA분석가, 피처엔지니어, 통계분석가, 감성분석가, 섹터분석가
//   - ML팀: 모델트레이너, 백테스터, 리스크평가자
//   - 보고서팀: 종합리포터, 투자메모작성자, 리스크노트작성자, 편집장
// - 현재 처리 중인 종목
// - 전체 진행률 바
// - ML 모델 학습 세부 상태 (Epoch/Trial)
```

### 6.7 활동 로그

```typescript
// dashboard/ActivityLog.tsx

// 실시간 활동 로그 스트림
// 예시:
// [10:30:05] 🔍 수집팀 - 삼성전자(005930) 주가 데이터 수집 시작
// [10:30:18] ✅ 수집팀 - 삼성전자 데이터 수집 완료 (120건)
// [10:30:19] 📤 수집팀 → 분석팀 원시 데이터 전달
// [10:30:20] 📊 분석팀/EDA - 삼성전자 탐색적 데이터 분석 시작
// [10:30:25] 📊 분석팀/EDA - ADF 검정 p=0.023 (정상 시계열)
// [10:30:30] 💬 분석팀/감성 - TF-IDF + LLM 감성분석 병렬 진행
// [10:30:35] 🔧 분석팀/피처 - 52개 피처 생성, 상호정보량 기반 30개 선택
// [10:30:40] 📈 분석팀/통계 - Granger 인과성 검정 | GARCH 변동성 모델
// [10:30:50] ✅ 분석팀 - 삼성전자 데이터사이언스 분석 완료
// [10:30:51] 📤 분석팀 → ML팀 피처셋 + 분석결과 전달
// [10:31:00] 🤖 ML팀/모델 - Prophet 학습 시작
// [10:31:10] 🤖 ML팀/모델 - LSTM 학습 중 (Epoch 25/50, Loss: 0.031)
// [10:31:20] 🤖 ML팀/모델 - XGBoost Optuna 최적화 (Trial 15/30)
// [10:31:30] 🤖 ML팀/모델 - 앙상블 가중치 최적화 완료
// [10:31:35] 🧪 ML팀/백테스트 - Walk-Forward Validation (5 splits)
// [10:31:40] ⚠️ ML팀/리스크 - VaR 95% = -2.8%, Monte Carlo 시뮬레이션
// [10:31:50] ✅ ML팀 - 삼성전자 ML 분석 완료
// [10:31:51] 📤 ML팀 → 보고서팀 ML결과 + 백테스트 + 리스크 전달
// [10:31:52] 📝 보고서팀/종합 - 수집·분석·ML 결과 종합 리포트 작성 시작
// [10:31:55] 📊 보고서팀/투자메모 - 투자 의견 메모 작성 중 (매수 추천)
// [10:31:58] ⚠️ 보고서팀/리스크노트 - 리스크 경고 노트 작성 중 (VaR 주의)
// [10:32:05] ✅ 보고서팀/종합 - 종합 리포트 초안 완료 → 편집장 전달
// [10:32:10] ✏️ 보고서팀/편집장 - 최종 보고서 검토 및 편집 중
// [10:32:15] ✅ 보고서팀/편집장 - 최종 보고서 승인 완료
// [10:32:16] 📱 텔레그램으로 최종 보고서 전송 완료
```

## 7. 캐릭터 디자인 가이드

### 7.1 팀별 캐릭터 특징

```
수집팀 (Collection Team)
- 색상: 초록 계열 (#4CAF50)
- 복장: 돋보기 + 서류가방
- 책상 소품: 모니터 여러 대, 데이터 스트림 화면
- 특수 이펙트: 데이터 입자가 모니터에서 나옴

분석팀 - EDA 분석가 (EDA Analyst)
- 색상: 시안 계열 (#00BCD4)
- 복장: 안경 + 히스토그램 패드
- 책상 소품: 분포 차트 화면, Q-Q Plot, ACF/PACF 그래프
- 특수 이펙트: 히스토그램 막대가 위로 생성됨

분석팀 - 피처 엔지니어 (Feature Engineer)
- 색상: 갈색 계열 (#795548)
- 복장: 톱니바퀴 아이콘 모자 + 도구 벨트
- 책상 소품: 데이터 테이블 화면, 피처 파이프라인 다이어그램
- 특수 이펙트: 기어/톱니가 회전하며 데이터 변환

분석팀 - 통계 분석가 (Statistical Analyst)
- 색상: 파란 계열 (#2196F3)
- 복장: 안경 + 수식 보드
- 책상 소품: 회귀선 차트, 화이트보드 (p-value, 수식)
- 특수 이펙트: 수학 공식이 공중에 떠다님

ML팀 - 모델 트레이너 (Model Trainer)
- 색상: 핑크 계열 (#E91E63)
- 복장: 뉴럴넷 로고 티셔츠
- 책상 소품: GPU 서버 랙, Loss 곡선 모니터, MLflow 대시보드
- 특수 이펙트: 뉴런 연결 파티클이 수렴 (Loss 감소 시각화)

ML팀 - 백테스터 (Backtester)
- 색상: 청록 계열 (#009688)
- 복장: 시계 + 차트 도구
- 책상 소품: 캔들 차트 화면, 매수/매도 시그널 패널
- 특수 이펙트: 차트 위에 초록(매수)/빨강(매도) 화살표

ML팀 - 리스크 평가자 (Risk Assessor)
- 색상: 주황 계열 (#FF9800)
- 복장: 방패 아이콘 + 경고 표시
- 책상 소품: VaR 게이지, Monte Carlo 시뮬레이션 Fan 차트
- 특수 이펙트: 경고 삼각형이 펄스하며 깜박임

───────────────────────────────────

보고서팀 - 종합 리포터 (Comprehensive Reporter)
- 색상: 보라 계열 (#9C27B0)
- 복장: 펜 + 두꺼운 보고서 바인더
- 책상 소품: 멀티 모니터 (ML결과+EDA+백테스트 동시 표시), LLM 대화창
- 특수 이펙트: 여러 색 문서 파티클이 하나로 합쳐지며 보고서 생성
- 역할: 수집·분석·ML팀의 전체 결과를 종합하여 최종 리포트 작성

보고서팀 - 투자 메모 작성자 (Investment Memo Writer)
- 색상: 남색 계열 (#1A237E)
- 복장: 정장 + 금융 차트 클립보드
- 책상 소품: 종목별 요약 카드, 투자 의견 보드
- 특수 이펙트: 매수/매도 신호가 텍스트로 변환되는 파티클
- 역할: ML 예측 + 백테스트 결과를 투자 판단 관점에서 요약

보고서팀 - 리스크 노트 작성자 (Risk Note Writer)
- 색상: 딥오렌지 계열 (#BF360C)
- 복장: 경고 배지 + 방패 문서
- 책상 소품: VaR 요약 화면, 리스크 매트릭스 보드
- 특수 이펙트: 경고 삼각형이 문서 아이콘으로 변환
- 역할: 리스크 평가 결과를 경고 수준별로 정리하여 리스크 노트 작성

보고서팀 - 편집장 (Report Editor / Chief)
- 색상: 금색 계열 (#F9A825)
- 복장: 편집장 모자 + 빨간 펜
- 책상 소품: 최종 보고서 미리보기 화면, 텔레그램 전송 버튼
- 특수 이펙트: 빨간 체크 파티클 (교정) → 금색 완료 파티클 (승인)
- 역할: 모든 보고서를 최종 검토·편집 후 텔레그램으로 발송

배달 캐릭터 (Delivery)
- 색상: 주황 계열 (#FF9800)
- 복장: 서류 봉투 든 모습
- 경로: 복도를 따라 팀 방 사이를 이동
- 전달 종류: raw_data, eda_report, features, ml_predictions, backtest_results, comprehensive_report, investment_memo, risk_note
- 특수 이펙트: 뒤에 서류 파티클 흩날림 (전달 유형별 색상 다름)
```

### 7.2 스프라이트 시트 구조

```
각 캐릭터 스프라이트 시트:
- 크기: 32x48px per frame  (가로 32 × 세로 48, 2:3 비율로 자연스러운 인체 비율)
- 시트 총 크기: 256 × 144px  (가로 8프레임 × 32 / 세로 3행 × 48)
- PixiJS scale: 2.0  →  화면 표시 크기 64×96px
- 공통 프레임 (row 0~1):
  - idle: 4프레임 (앉아서 대기, 미세 움직임)
  - typing: 6프레임 (타이핑 모션)
  - reading: 4프레임 (문서 읽기)
  - writing: 6프레임 (문서 작성)
  - walking: 8프레임 (이동, 상하좌우)
  - celebrating: 4프레임 (완료 축하)
  - error: 2프레임 (에러 상태)
- 역할별 추가 프레임 (row 2):
  - eda_analyzing: 6프레임 (차트 응시 + 고개 끄덕)
  - feature_building: 6프레임 (기어 조립 모션)
  - model_training: 8프레임 (모니터 집중 + GPU LED 깜박)
  - optimizing: 6프레임 (여러 모니터 사이 고개 돌리기)
  - backtesting: 6프레임 (차트 스크롤 모션)
  - risk_checking: 4프레임 (경고 게이지 확인)
  - report_writing: 6프레임 (타이핑 + 문서 합치기 모션)
  - reviewing: 6프레임 (문서 넘기며 빨간 펜 교정)
  - summarizing: 8프레임 (여러 문서 → 하나로 합치기)

가구/소품 스프라이트:
- 책상·모니터: 32×32px
- GPU 서버 랙: 32×64px  (캐릭터보다 약간 큼)
- 배달 서류: 16×16px  (작게 날아다니는 느낌)
- 바닥 타일: 16×16px
```

### 7.3 캔버스 & 레이아웃 상수

```typescript
// office-view/model.ts 에 추가
export const CANVAS_CONFIG = {
  // 논리 해상도 (CSS px) — 뷰포트 60% 영역
  WIDTH: 960,
  HEIGHT: 640,

  // 캐릭터 스프라이트 원본 크기
  SPRITE_W: 32,
  SPRITE_H: 48,
  CHARACTER_SCALE: 2.0,   // 화면 표시: 64×96px

  // 가구·소품
  FURNITURE_SIZE: 32,     // 책상·모니터 32×32px
  GPU_SERVER_H: 64,       // GPU 서버 랙 32×64px
  DELIVERY_SIZE: 16,      // 배달 서류 16×16px

  // 타일 (바닥·벽 그리드 기준)
  TILE_SIZE: 16,

  // 팀 방
  ROOM_W: 260,
  ROOM_H: 150,
  ROOM_GAP: 10,           // 방 사이 여백
  ROOM_PADDING: 12,       // 방 내부 여백

  // 복도 (배달 경로 + ML 현황 패널)
  CORRIDOR_W: 420,

  // HiDPI 대응 (Retina 등)
  RESOLUTION: typeof window !== "undefined" ? window.devicePixelRatio : 1,
} as const;
```

## 8. 반응형 레이아웃

```typescript
// 브레이크포인트별 레이아웃
const LAYOUT_CONFIG = {
  desktop: {    // > 1280px
    officeWidth: "60%",
    dashboardWidth: "40%",
    showChatPanel: true,
  },
  tablet: {     // 768px ~ 1280px
    officeWidth: "100%",
    dashboardWidth: "100%",   // 탭 전환
    showChatPanel: false,     // 별도 탭
  },
  mobile: {     // < 768px
    officeWidth: "100%",
    dashboardWidth: "100%",   // 탭 전환
    showChatPanel: false,
    simplifiedOffice: true,   // 간소화된 오피스 뷰
  },
};
```
