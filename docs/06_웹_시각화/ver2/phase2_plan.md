# Phase 2 계획서 — 웹 시각화 고도화

> v2 기반, Phase 1 완료 후 다음 단계

---

## Phase 1 완료 요약 (현재 상태)

### 구현 완료

| 구분 | 내용 | 상태 |
|------|------|------|
| **레이아웃** | 3-Column Bloomberg 터미널 스타일 | ✅ |
| **시장 탭** | 시총 TOP6 캔들차트 + 지수 카드 + 뉴스 5건 | ✅ |
| **오피스 탭** | 4팀 방 + CEO실 + 복도 + 편의시설 | ✅ |
| **에이전트 패널** | 좌측 216px, 팀별 에이전트 상태 | ✅ |
| **활동 로그** | 우측 196px, 타임스탬프 이벤트 | ✅ |
| **배달 시스템** | 서무 직접 이동, 파이프라인 순차, 일정 속도 | ✅ |
| **CEO실** | 코너 오피스, 책장, 트로피, 파노라마 창 | ✅ |
| **편의시설** | 회의실, 휴게실, 화장실, 엘리베이터 | ✅ |
| **테마** | 다크/라이트 토글 | ✅ |
| **차트** | Canvas 2D 캔들스틱 (StockChart.tsx) | ✅ |
| **서무 시스템** | 각 방 서무(delivery), 배달 후 귀환 | ✅ |
| **OUTBOX 트레이** | 각 방 문 옆 서류 트레이 | ✅ |

### 현재 파일 구조

```
src/web-service/
├── src/
│   ├── App.tsx          # 전체 (~1,300행, 단일 파일)
│   ├── StockChart.tsx   # 캔들차트 컴포넌트
│   ├── index.css        # CSS 변수, 애니메이션
│   └── main.tsx         # 진입점
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 기술적 부채

- `App.tsx` 단일 파일 1,300행 — 컴포넌트 분리 필요
- 모든 데이터가 mock (하드코딩) — WebSocket 연동 필요
- 캐릭터가 Canvas 2D 프로시저럴 — 스프라이트시트 미적용
- pixi.js가 package.json에 남아있음 (미사용)

---

## Phase 2 목표

### P2-1. App.tsx 분리 리팩토링

**우선순위: 높음** — 이후 모든 작업의 기반

```
src/
├── components/
│   ├── office/
│   │   ├── OfficeCanvas.tsx      # RAF 루프 + Canvas 관리
│   │   ├── drawOffice.ts         # drawOffice 메인 함수
│   │   ├── drawRoom.ts           # drawRoomFloor, drawRoomWalls, drawRoomProps
│   │   ├── drawCEORoom.ts        # drawCEORoom
│   │   ├── drawCorridor.ts       # 복도, 편의시설
│   │   ├── drawCharacter.ts      # drawPixelChar, drawDesk
│   │   ├── drawDelivery.ts       # 배달 경로 계산 + 렌더링
│   │   └── constants.ts          # INITIAL_CHARS, STATE_INFO
│   ├── panels/
│   │   ├── AgentStatusPanel.tsx
│   │   ├── ActivityLogPanel.tsx
│   │   └── MarketPanel.tsx
│   ├── chart/
│   │   └── StockChart.tsx        # (기존 파일 이동)
│   └── layout/
│       ├── Header.tsx
│       └── MainPanel.tsx
├── theme/
│   ├── colors.ts                 # DARK, LIGHT, Colors 타입
│   └── ThemeContext.tsx           # ThemeContext, useTheme
├── types/
│   └── index.ts                  # Character, Delivery, Particle 등
├── App.tsx                       # 루트 조합만
├── index.css
└── main.tsx
```

### P2-2. 커스텀 스프라이트 적용

**우선순위: 높음** — 시각적 품질 결정

| 단계 | 작업 | 도구 |
|------|------|------|
| 1 | 캐릭터 스프라이트시트 제작 | **Aseprite** (유료, 업계 표준) 또는 **Piskel** (무료 웹) |
| 2 | 스프라이트 사양 결정 | 32×48px 원본, 4방향(상하좌우), 3프레임 워킹 |
| 3 | `public/assets/sprites/{role}.png` 배치 | PNG 파일 |
| 4 | `getSprite()` → 스프라이트시트 파싱 로직 | AnimatedSprite 로더 |
| 5 | 방향별 + 상태별 프레임 매핑 | walk_down_0, walk_down_1, ... |

**스프라이트 사양:**

```
파일명: {role}.png (예: collector.png, eda_analyst.png)
크기: 128×192px (4열 × 4행)
  열: frame0, frame1, frame2, frame3
  행: down, left, right, up
프레임 크기: 32×48px
스케일: 2.0x → 화면 64×96px
```

**필요 스프라이트 (23종):**
- 수집팀: collector (×3 변형), delivery
- 분석팀: eda_analyst, feature_engineer, stat_analyst, sentiment, sector_cluster, delivery
- ML팀: ml_engineer (×2 변형), backtester, risk_assessor, delivery
- 보고서팀: report_writer, invest_memo, risk_note, editor, delivery
- CEO: ceo
- 배달원: courier (복도 이동 시 공용)

### P2-3. WebSocket 실시간 데이터 연동

**우선순위: 중간** — 백엔드 준비도에 따라

```typescript
// hooks/useWebSocket.ts
export function useWebSocket(url: string) {
  const [connected, setConnected] = useState(false)
  const eventHandlers = useRef(new Map<string, Function[]>())

  useEffect(() => {
    const ws = new WebSocket(url)
    ws.onopen = () => setConnected(true)
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)
      // event.type: 'agent_state' | 'delivery' | 'market' | 'log'
      eventHandlers.current.get(event.type)?.forEach(fn => fn(event.data))
    }
    return () => ws.close()
  }, [url])

  return { connected, on: (type, fn) => ... }
}
```

**연동 대상:**

| 이벤트 | 소스 | 적용 위치 |
|--------|------|----------|
| `agent_state` | Prefect flow 이벤트 | 캐릭터 상태 전환 |
| `delivery_start` | flow 간 데이터 전달 | 서무 배달 트리거 |
| `market_data` | 키움 API / KRX | 시장 탭 차트 업데이트 |
| `log_entry` | structlog | 활동 로그 추가 |
| `model_progress` | MLflow callback | 에이전트 진행률 |

### P2-4. Kiwoom API 실시간 시세 연동

**우선순위: 중간** — P2-3 이후

```
1. 키움 OpenAPI 토큰 발급 (OAuth2 client_credentials)
2. REST 폴링 또는 WebSocket 구독
3. 실시간 체결가 → 캔들차트 업데이트
4. 호가/체결 → 활동 로그 피드
5. 시장 지수 → Header 티커 실시간
```

### P2-5. 오피스 디자인 고도화

**우선순위: 낮음** — 스프라이트 준비 후

| 항목 | 현재 | Phase 2 목표 |
|------|------|-------------|
| 캐릭터 | 프로시저럴 픽셀 (코드로 그림) | Aseprite 스프라이트시트 |
| 가구 | 코드 직접 그리기 | 스프라이트 에셋 또는 SVG |
| 바닥 | 단색 + 격자 | 타일맵 텍스처 |
| 벽 | 단색 라인 | 텍스처 벽면 |
| 조명 | radialGradient | 동적 그림자 + 광원 |

### P2-6. 디자인 → 코드 파이프라인 구축

**디자이너 협업 워크플로:**

```
[Figma / Aseprite]
    ↓ 디자이너 작업
[에셋 Export]
    ├── UI 레이아웃: Figma → Locofy/Builder.io → React 컴포넌트
    ├── 스프라이트: Aseprite → PNG 스프라이트시트
    └── 아이콘/가구: Figma SVG export
    ↓
[public/assets/]
    ├── sprites/{role}.png
    ├── furniture/{item}.png
    └── ui/{icon}.svg
    ↓
[프론트엔드 자동 로드]
    ├── getSprite(role) → 캐릭터 로드
    └── React 컴포넌트 import
```

**추천 도구:**

| 용도 | 도구 | 비용 |
|------|------|------|
| 픽셀 캐릭터 | [Aseprite](https://www.aseprite.org) | $19.99 (1회) |
| 무료 대안 | [Piskel](https://www.piskelapp.com) | 무료 |
| UI 레이아웃 | [Figma](https://www.figma.com) | 무료~$15/월 |
| Figma → React | [Locofy.ai](https://www.locofy.ai) | 무료~$25/월 |
| Figma → React | [Builder.io](https://www.builder.io) | 무료 플러그인 |
| Figma → React | [Anima](https://www.animaapp.com) | 무료~$39/월 |

---

## Phase 2 마일스톤

| 주차 | 작업 | 산출물 |
|------|------|--------|
| **Week 1** | P2-1 App.tsx 분리 | 15+ 파일, 각 100행 이하 |
| **Week 2** | P2-2 스프라이트 사양 확정 + 샘플 제작 | 스프라이트시트 3종 |
| **Week 3** | P2-3 WebSocket 훅 + 목 서버 | useWebSocket.ts, 실시간 로그 |
| **Week 4** | P2-4 키움 API 연동 시작 | 시세 REST → 차트 업데이트 |
| **Week 5-6** | P2-5 오피스 디자인 고도화 | 스프라이트 적용, 타일맵 |

---

## Phase 2 완료 기준

- [ ] App.tsx 200행 이하 (조합 코드만)
- [ ] 최소 3개 캐릭터 커스텀 스프라이트 적용
- [ ] WebSocket 연결 → 에이전트 상태 실시간 반영
- [ ] 키움 API → 1개 이상 종목 실시간 시세
- [ ] 디자이너 에셋 전달 → 자동 반영 파이프라인 문서화
