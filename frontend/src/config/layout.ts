// ── 캔버스 = 배경 이미지 크기 (960×640) ─────────────────────────────────────
export const CANVAS = { WIDTH: 960, HEIGHT: 640 } as const;

// ── 팀 방 영역 (이미지 내 좌표, 대략적 히트맵) ─────────────────────────────
// 왼쪽 컬럼: 4개 팀룸 세로 배치
export const ROOMS = {
  collection: {
    label: "수집팀",
    labelEn: "COLLECTION",
    accentColor: 0x5b9bd5,
    // 이미지 내 방 영역 (px)
    x: 0, y: 0, w: 310, h: 155,
  },
  analysis: {
    label: "분석팀",
    labelEn: "ANALYSIS",
    accentColor: 0x6aab6a,
    x: 0, y: 155, w: 310, h: 155,
  },
  ml: {
    label: "ML팀",
    labelEn: "ML ENG",
    accentColor: 0xd4a840,
    x: 0, y: 310, w: 310, h: 155,
  },
  report: {
    label: "보고서팀",
    labelEn: "REPORT",
    accentColor: 0xc87aaf,
    x: 0, y: 465, w: 310, h: 175,
  },
} as const;

export type RoomKey = keyof typeof ROOMS;

// ── 가운데 영역 ─────────────────────────────────────────────────────────────
export const AUDITORIUM = { x: 310, y: 0, w: 340, h: 370 } as const;
export const LOBBY = { x: 310, y: 370, w: 340, h: 270 } as const;

// ── 오른쪽 영역 ─────────────────────────────────────────────────────────────
export const EXECUTIVE = { x: 650, y: 0, w: 310, h: 220 } as const;

// 큐비클 2×3
export const CUBICLES = [
  { x: 650, y: 220, w: 155, h: 140 },
  { x: 805, y: 220, w: 155, h: 140 },
  { x: 650, y: 360, w: 155, h: 140 },
  { x: 805, y: 360, w: 155, h: 140 },
  { x: 650, y: 500, w: 155, h: 140 },
  { x: 805, y: 500, w: 155, h: 140 },
] as const;
