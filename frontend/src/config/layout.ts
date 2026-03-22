// ── 캔버스 기본 사양 ─────────────────────────────────────────────────────────
export const CANVAS = { WIDTH: 960, HEIGHT: 640 } as const;

export const HEADER = { HEIGHT: 32 } as const;
export const FOOTER = { HEIGHT: 24 } as const;

// ── 컨텐츠 영역 ─────────────────────────────────────────────────────────────
// 가용 세로: 640 - 32 - 24 = 584px
const CONTENT_Y = HEADER.HEIGHT;
const CONTENT_H = CANVAS.HEIGHT - HEADER.HEIGHT - FOOTER.HEIGHT; // 584

// ── 오피스 / 대시보드 분할 (60% / 40%) ──────────────────────────────────────
export const OFFICE = {
  x: 0,
  y: CONTENT_Y,
  w: 576, // 960 * 0.60
  h: CONTENT_H,
} as const;

export const DASHBOARD = {
  x: 576,
  y: CONTENT_Y,
  w: 384, // 960 * 0.40
  h: CONTENT_H,
} as const;

// ── 팀 방 (260 × 140px, 좌측 열) ────────────────────────────────────────────
// 4 rooms × 140 + 3 gaps × 8 = 560 + 24 = 584 ✓ 정확히 맞춤
export const ROOM_W = 260;
export const ROOM_H = 140;
const ROOM_GAP = 8;

export const ROOMS = {
  collection: {
    label: "수집팀",
    labelEn: "COLLECTION",
    accentColor: 0x4caf50,
    bgColor: 0x0f1f0f,
    x: 0,
    y: CONTENT_Y + (ROOM_H + ROOM_GAP) * 0,
    w: ROOM_W,
    h: ROOM_H,
  },
  analysis: {
    label: "분석팀",
    labelEn: "ANALYSIS",
    accentColor: 0x00bcd4,
    bgColor: 0x081820,
    x: 0,
    y: CONTENT_Y + (ROOM_H + ROOM_GAP) * 1,
    w: ROOM_W,
    h: ROOM_H,
  },
  ml: {
    label: "ML팀",
    labelEn: "ML ENG",
    accentColor: 0xe91e63,
    bgColor: 0x1a0510,
    x: 0,
    y: CONTENT_Y + (ROOM_H + ROOM_GAP) * 2,
    w: ROOM_W,
    h: ROOM_H,
  },
  report: {
    label: "보고서팀",
    labelEn: "REPORT",
    accentColor: 0x9c27b0,
    bgColor: 0x100818,
    x: 0,
    y: CONTENT_Y + (ROOM_H + ROOM_GAP) * 3,
    w: ROOM_W,
    h: ROOM_H,
  },
} as const;

export type RoomKey = keyof typeof ROOMS;

// ── 복도 (오피스 내 우측 빈 공간) ───────────────────────────────────────────
export const CORRIDOR = {
  x: ROOM_W,
  y: CONTENT_Y,
  w: OFFICE.w - ROOM_W, // 316px
  h: CONTENT_H,
} as const;

// ── 바닥 타일 ────────────────────────────────────────────────────────────────
export const TILE = 16;
