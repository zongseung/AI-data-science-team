import * as PIXI from "pixi.js";
import { ROOMS } from "../config/layout";

// ═══════════════════════════════════════════════════════════════════════════
// 기본 가구 프리미티브
// ═══════════════════════════════════════════════════════════════════════════

function darken(c: number, t: number) {
  const r = Math.round(((c >> 16) & 0xff) * (1 - t));
  const g = Math.round(((c >> 8) & 0xff) * (1 - t));
  const b = Math.round((c & 0xff) * (1 - t));
  return (r << 16) | (g << 8) | b;
}
function lighten(c: number, t: number) {
  const r = Math.round(((c >> 16) & 0xff) + (255 - ((c >> 16) & 0xff)) * t);
  const g = Math.round(((c >> 8) & 0xff) + (255 - ((c >> 8) & 0xff)) * t);
  const b = Math.round((c & 0xff) + (255 - (c & 0xff)) * t);
  return (r << 16) | (g << 8) | b;
}

// 책상 (탑다운 뷰, 36×12px)
function desk(g: PIXI.Graphics, x: number, y: number, color: number) {
  // 측면 그림자
  g.rect(x + 2, y + 12, 36, 3).fill({ color: darken(color, 0.6) });
  // 상판
  g.rect(x, y, 36, 12).fill({ color }).stroke({ color: darken(color, 0.35), width: 1 });
  // 상판 하이라이트
  g.rect(x + 1, y + 1, 34, 2).fill({ color: lighten(color, 0.12) });
  // 다리
  g.rect(x + 2, y + 12, 5, 5).fill({ color: darken(color, 0.4) });
  g.rect(x + 29, y + 12, 5, 5).fill({ color: darken(color, 0.4) });
}

// 모니터 (16×14px, 화면 포함)
function monitor(g: PIXI.Graphics, x: number, y: number, screenColor: number) {
  // 받침대 베이스
  g.rect(x + 4, y + 14, 8, 2).fill({ color: 0x1a1a28 });
  g.rect(x + 6, y + 12, 4, 2).fill({ color: 0x222235 });
  // 베젤
  g.rect(x, y, 16, 12).fill({ color: 0x12121e }).stroke({ color: 0x2a2a3a, width: 1 });
  // 화면
  g.rect(x + 1, y + 1, 14, 9).fill({ color: screenColor });
  // 화면 내부 픽셀 선
  g.rect(x + 1, y + 4, 14, 1).fill({ color: darken(screenColor, 0.4) });
  g.rect(x + 1, y + 7, 14, 1).fill({ color: darken(screenColor, 0.3) });
  // 전원 LED
  g.rect(x + 13, y + 11, 2, 1).fill({ color: lighten(screenColor, 0.4) });
}

// 키보드 (14×5px)
function keyboard(g: PIXI.Graphics, x: number, y: number) {
  g.rect(x, y, 14, 5).fill({ color: 0x14141f }).stroke({ color: 0x222230, width: 1 });
  // 키 줄
  for (let row = 0; row < 2; row++) {
    for (let col = 0; col < 6; col++) {
      g.rect(x + 1 + col * 2, y + 1 + row * 2, 1, 1).fill({ color: 0x282838 });
    }
  }
}

// GPU 서버 랙 (18×36px)
function gpuRack(g: PIXI.Graphics, x: number, y: number) {
  // 본체
  g.rect(x, y, 18, 36).fill({ color: 0x0e0e18 }).stroke({ color: 0x2a2a3a, width: 1 });
  // 상단 하이라이트
  g.rect(x + 1, y + 1, 16, 2).fill({ color: 0x1a1a28 });

  // 슬롯 4개
  const ledColors = [0xe91e63, 0xe91e63, 0x2196f3, 0x4caf50];
  for (let i = 0; i < 4; i++) {
    const sy = y + 5 + i * 8;
    g.rect(x + 2, sy, 14, 6).fill({ color: 0x141420 }).stroke({ color: 0x222230, width: 1 });
    // 슬롯 라인
    g.rect(x + 3, sy + 2, 9, 1).fill({ color: 0x1e1e2e });
    g.rect(x + 3, sy + 4, 9, 1).fill({ color: 0x1e1e2e });
    // LED
    g.circle(x + 14, sy + 3, 1.5).fill({ color: ledColors[i] });
  }

  // 벤트 슬릿 (하단)
  for (let i = 0; i < 3; i++) {
    g.rect(x + 3, y + 38 - 8 + i * 2, 12, 1).fill({ color: 0x1a1a28 });
  }
}

// 수납장 (20×14px)
function cabinet(g: PIXI.Graphics, x: number, y: number, color: number) {
  g.rect(x + 1, y + 14, 20, 3).fill({ color: darken(color, 0.55) });
  g.rect(x, y, 20, 14).fill({ color }).stroke({ color: darken(color, 0.35), width: 1 });
  // 상단 하이라이트
  g.rect(x + 1, y + 1, 18, 2).fill({ color: lighten(color, 0.08) });
  // 서랍 구분선
  g.rect(x + 2, y + 6, 16, 1).fill({ color: darken(color, 0.3) });
  // 손잡이
  g.rect(x + 7, y + 2, 6, 2).fill({ color: darken(color, 0.5) });
  g.rect(x + 7, y + 8, 6, 2).fill({ color: darken(color, 0.5) });
}

// 화분 (8×10px)
function plant(g: PIXI.Graphics, x: number, y: number) {
  // 화분
  g.rect(x + 1, y + 6, 6, 4).fill({ color: 0x5d3a1a });
  g.rect(x + 2, y + 9, 4, 1).fill({ color: 0x3e2510 });
  // 흙
  g.rect(x + 2, y + 5, 4, 2).fill({ color: 0x2d1a08 });
  // 잎
  g.circle(x + 4, y + 3, 3).fill({ color: 0x2d6a2d });
  g.circle(x + 2, y + 4, 2).fill({ color: 0x387038 });
  g.circle(x + 6, y + 4, 2).fill({ color: 0x2d6a2d });
}

// ═══════════════════════════════════════════════════════════════════════════
// 팀별 배치
// ═══════════════════════════════════════════════════════════════════════════

function placeCollection(g: PIXI.Graphics) {
  const { x, y } = ROOMS.collection;
  const ox = x + 14;
  const oy = y + 24;

  // 상단 책상 열 (3개)
  for (let i = 0; i < 3; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy, 0x1a3020);
    monitor(g, dx + 10, oy - 16, 0x001a08);
    keyboard(g, dx + 11, oy + 2);
  }

  // 하단 책상 열 (2개)
  for (let i = 0; i < 2; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy + 58, 0x1a3020);
    monitor(g, dx + 10, oy + 58 - 16, 0x002210);
    keyboard(g, dx + 11, oy + 58 + 2);
  }

  // 수납장 + 화분
  cabinet(g, ox + 172, oy, 0x18281a);
  cabinet(g, ox + 196, oy, 0x18281a);
  plant(g, ox + 220, oy - 8);
}

function placeAnalysis(g: PIXI.Graphics) {
  const { x, y } = ROOMS.analysis;
  const ox = x + 14;
  const oy = y + 24;

  for (let i = 0; i < 3; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy, 0x0d2030);
    monitor(g, dx + 10, oy - 16, 0x001520);
    keyboard(g, dx + 11, oy + 2);
  }

  // 추가 모니터 (분석팀은 듀얼)
  monitor(g, ox + 10 - 18, oy - 16, 0x001020);

  for (let i = 0; i < 2; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy + 58, 0x0d2030);
    monitor(g, dx + 10, oy + 58 - 16, 0x00182a);
    keyboard(g, dx + 11, oy + 58 + 2);
  }

  cabinet(g, ox + 172, oy, 0x0a1c28);
  plant(g, ox + 220, oy - 8);
}

function placeMl(g: PIXI.Graphics) {
  const { x, y } = ROOMS.ml;
  const ox = x + 14;
  const oy = y + 24;

  for (let i = 0; i < 3; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy, 0x1e0810);
    monitor(g, dx + 10, oy - 16, 0x180008);
    keyboard(g, dx + 11, oy + 2);
  }

  // GPU 랙 2개 (ML팀 특징)
  gpuRack(g, ox + 170, oy - 8);
  gpuRack(g, ox + 192, oy - 8);

  for (let i = 0; i < 2; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy + 58, 0x1e0810);
    monitor(g, dx + 10, oy + 58 - 16, 0x160006);
    keyboard(g, dx + 11, oy + 58 + 2);
  }
}

function placeReport(g: PIXI.Graphics) {
  const { x, y } = ROOMS.report;
  const ox = x + 14;
  const oy = y + 24;

  // 보고서팀 - 듀얼/트리플 모니터
  for (let i = 0; i < 3; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy, 0x120a1c);
    monitor(g, dx + 5, oy - 16, 0x0a0014);
    monitor(g, dx + 23, oy - 16, 0x0c0018);
    keyboard(g, dx + 11, oy + 2);
  }

  for (let i = 0; i < 2; i++) {
    const dx = ox + i * 54;
    desk(g, dx, oy + 58, 0x120a1c);
    monitor(g, dx + 10, oy + 58 - 16, 0x0a0014);
    keyboard(g, dx + 11, oy + 58 + 2);
  }

  cabinet(g, ox + 172, oy, 0x0f0a1a);
  cabinet(g, ox + 196, oy, 0x0f0a1a);
  plant(g, ox + 220, oy - 8);
}

// ═══════════════════════════════════════════════════════════════════════════
// 공개 API
// ═══════════════════════════════════════════════════════════════════════════
export function drawFurniture(g: PIXI.Graphics) {
  placeCollection(g);
  placeAnalysis(g);
  placeMl(g);
  placeReport(g);
}
