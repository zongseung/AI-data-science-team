import * as PIXI from "pixi.js";
import {
  CANVAS, HEADER, FOOTER,
  OFFICE, DASHBOARD, CORRIDOR,
  ROOMS, ROOM_W, TILE,
} from "../config/layout";

// ═══════════════════════════════════════════════════════════════════════════
// 유틸
// ═══════════════════════════════════════════════════════════════════════════
function hex(r: number, g: number, b: number) {
  return (r << 16) | (g << 8) | b;
}
function darken(color: number, t: number) {
  const r = Math.round(((color >> 16) & 0xff) * (1 - t));
  const g = Math.round(((color >> 8) & 0xff) * (1 - t));
  const b = Math.round((color & 0xff) * (1 - t));
  return (r << 16) | (g << 8) | b;
}
function lighten(color: number, t: number) {
  const r = Math.round(((color >> 16) & 0xff) + (255 - ((color >> 16) & 0xff)) * t);
  const g = Math.round(((color >> 8) & 0xff) + (255 - ((color >> 8) & 0xff)) * t);
  const b = Math.round((color & 0xff) + (255 - (color & 0xff)) * t);
  return (r << 16) | (g << 8) | b;
}

// ═══════════════════════════════════════════════════════════════════════════
// 체커보드 바닥 타일
// ═══════════════════════════════════════════════════════════════════════════
function drawTiles(
  g: PIXI.Graphics,
  x: number, y: number, w: number, h: number,
  colorA: number, colorB: number,
  lineColor: number,
) {
  for (let ty = y; ty < y + h; ty += TILE) {
    for (let tx = x; tx < x + w; tx += TILE) {
      const even = ((Math.floor((tx - x) / TILE) + Math.floor((ty - y) / TILE)) % 2) === 0;
      g.rect(tx, ty, TILE, TILE).fill({ color: even ? colorA : colorB });
    }
  }
  // 가로 그리드 라인
  for (let ty = y; ty <= y + h; ty += TILE) {
    g.rect(x, ty, w, 1).fill({ color: lineColor });
  }
  // 세로 그리드 라인
  for (let tx = x; tx <= x + w; tx += TILE) {
    g.rect(tx, y, 1, h).fill({ color: lineColor });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// 헤더
// ═══════════════════════════════════════════════════════════════════════════
function drawHeader(g: PIXI.Graphics) {
  // 배경
  g.rect(0, 0, CANVAS.WIDTH, HEADER.HEIGHT).fill({ color: 0x05050d });
  // 구분선
  g.rect(0, HEADER.HEIGHT - 1, CANVAS.WIDTH, 1).fill({ color: 0x1a1a33 });
  // 상단 픽셀 테두리
  g.rect(0, 0, CANVAS.WIDTH, 2).fill({ color: 0x111122 });

  // 마켓 데이터 칩
  const chips = [
    { label: "KOSPI",   value: "2,730.45", delta: "+0.32%", up: true,  x: 8 },
    { label: "KOSDAQ",  value: "875.12",   delta: "-0.11%", up: false, x: 168 },
    { label: "USD/KRW", value: "1,328.5",  delta: "+2.10",  up: false, x: 328 },
  ];
  for (const c of chips) {
    // 칩 배경
    g.rect(c.x, 6, 152, 20).fill({ color: 0x0d0d1a }).stroke({ color: 0x1e1e33, width: 1 });
    // 좌측 컬러 바
    g.rect(c.x, 6, 3, 20).fill({ color: c.up ? 0x4caf50 : 0xf44336 });
  }

  // 시스템 상태 도트 (우측)
  const dots = [
    { color: 0x4caf50, x: CANVAS.WIDTH - 120 },
    { color: 0x2196f3, x: CANVAS.WIDTH - 100 },
    { color: 0xff9800, x: CANVAS.WIDTH - 80 },
    { color: 0x29b6f6, x: CANVAS.WIDTH - 60 },
  ];
  for (const d of dots) {
    g.circle(d.x, 16, 4).fill({ color: d.color });
    g.circle(d.x, 16, 3).fill({ color: lighten(d.color, 0.3) });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// 푸터
// ═══════════════════════════════════════════════════════════════════════════
function drawFooter(g: PIXI.Graphics) {
  const y = CANVAS.HEIGHT - FOOTER.HEIGHT;
  g.rect(0, y, CANVAS.WIDTH, FOOTER.HEIGHT).fill({ color: 0x05050d });
  g.rect(0, y, CANVAS.WIDTH, 1).fill({ color: 0x1a1a33 });
  // 스캔라인 느낌
  g.rect(0, y + 1, CANVAS.WIDTH, 1).fill({ color: hex(10, 10, 20) });
}

// ═══════════════════════════════════════════════════════════════════════════
// 팀 방
// ═══════════════════════════════════════════════════════════════════════════
function drawRoom(g: PIXI.Graphics, room: (typeof ROOMS)[keyof typeof ROOMS]) {
  const { x, y, w, h, bgColor, accentColor } = room;

  // ── 바닥 타일 ──────────────────────────────────────────────────────────
  const tileA = darken(bgColor, 0) ;
  const tileB = darken(bgColor, 0.12);
  const lineC = darken(bgColor, 0.25);
  drawTiles(g, x + 2, y + 20, w - 4, h - 22, tileA, tileB, lineC);

  // ── 외벽 ───────────────────────────────────────────────────────────────
  // 바깥 테두리 (2px 픽셀 느낌)
  g.rect(x, y, w, h).fill({ color: 0 }).stroke({ color: darken(accentColor, 0.5), width: 2 });
  // 안쪽 코너 하이라이트
  g.rect(x + 2, y + 20, w - 4, 1).fill({ color: darken(accentColor, 0.4) });

  // ── 상단 네임바 ────────────────────────────────────────────────────────
  const barH = 18;
  g.rect(x + 1, y + 1, w - 2, barH).fill({ color: darken(accentColor, 0.72) });
  // 네임바 하단 그림자
  g.rect(x + 1, y + barH, w - 2, 2).fill({ color: darken(accentColor, 0.85) });

  // 좌측 수직 액센트 바
  g.rect(x + 1, y + 1, 3, barH).fill({ color: accentColor });

  // ── 우측 출입구 (복도 쪽 문) ───────────────────────────────────────────
  const doorY = y + h / 2 - 14;
  const doorW = 4;
  const doorH = 28;
  g.rect(x + w - 2, doorY, doorW, doorH).fill({ color: darken(accentColor, 0.3) });
  // 문 경첩
  g.rect(x + w, doorY + 4, 2, 4).fill({ color: accentColor });
  g.rect(x + w, doorY + doorH - 8, 2, 4).fill({ color: accentColor });
}

// ═══════════════════════════════════════════════════════════════════════════
// 방 사이 구분 갭 (어두운 칸막이)
// ═══════════════════════════════════════════════════════════════════════════
function drawRoomDividers(g: PIXI.Graphics) {
  const gaps = [
    ROOMS.collection.y + ROOMS.collection.h,
    ROOMS.analysis.y + ROOMS.analysis.h,
    ROOMS.ml.y + ROOMS.ml.h,
  ];
  for (const gy of gaps) {
    g.rect(0, gy, ROOM_W, 8).fill({ color: 0x020205 });
    g.rect(0, gy + 1, ROOM_W, 1).fill({ color: 0x111118 });
    g.rect(0, gy + 6, ROOM_W, 1).fill({ color: 0x111118 });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// 복도
// ═══════════════════════════════════════════════════════════════════════════
function drawCorridor(g: PIXI.Graphics) {
  const { x, y, w, h } = CORRIDOR;

  // 바닥
  drawTiles(g, x, y, w, h, 0x0c0c16, 0x0a0a12, 0x111118);

  // 좌측 벽 (방과 복도 경계)
  g.rect(x, y, 2, h).fill({ color: 0x1a1a2a });
  // 우측 벽 (오피스/대시보드 경계)
  g.rect(x + w - 2, y, 2, h).fill({ color: 0x1a1a2a });

  // 복도 중앙 안내선 (점선 느낌)
  const centerX = x + w / 2;
  for (let dy = y + 8; dy < y + h; dy += 16) {
    g.rect(centerX - 1, dy, 2, 8).fill({ color: 0x1e1e2e });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// 대시보드
// ═══════════════════════════════════════════════════════════════════════════
function drawDashboard(g: PIXI.Graphics) {
  const { x, y, w, h } = DASHBOARD;

  // 전체 배경
  g.rect(x, y, w, h).fill({ color: 0x06060f });

  // 좌측 경계 (오피스 / 대시보드)
  g.rect(x, y, 2, h).fill({ color: 0x1a1a2e });
  g.rect(x + 2, y, 1, h).fill({ color: 0x111120 });

  // ── 서브 패널 4개 ────────────────────────────────────────────────────────
  const panels = [
    { label: "MARKET",    color: 0x4caf50 },
    { label: "ML MODEL",  color: 0xe91e63 },
    { label: "BACKTEST",  color: 0x009688 },
    { label: "REPORTS",   color: 0x9c27b0 },
  ];
  const panelW = w - 16;
  const panelH = Math.floor((h - 24) / 4) - 4;

  panels.forEach((p, i) => {
    const py = y + 8 + i * (panelH + 6);
    const px = x + 8;

    // 패널 배경
    g.rect(px, py, panelW, panelH)
      .fill({ color: 0x0b0b18 })
      .stroke({ color: darken(p.color, 0.6), width: 1 });

    // 상단 액센트 바 (3px)
    g.rect(px + 1, py + 1, panelW - 2, 3).fill({ color: darken(p.color, 0.35) });

    // 좌측 컬러 바
    g.rect(px + 1, py + 4, 2, panelH - 5).fill({ color: darken(p.color, 0.45) });

    // 더미 차트 라인 (픽셀 그래프 느낌)
    const chartX = px + 10;
    const chartY = py + 22;
    const chartW = panelW - 20;
    const chartH = panelH - 32;

    // 배경 그리드
    for (let gy = chartY; gy < chartY + chartH; gy += 8) {
      g.rect(chartX, gy, chartW, 1).fill({ color: 0x111120 });
    }

    // 더미 바 차트
    const barCount = Math.floor(chartW / 10);
    for (let bi = 0; bi < barCount; bi++) {
      const bh = Math.floor(Math.sin(bi * 0.7 + i) * (chartH / 3) + chartH / 2);
      const bc = bi % 3 === 0 ? lighten(p.color, 0) : darken(p.color, 0.3);
      g.rect(chartX + bi * 10, chartY + chartH - bh, 8, bh).fill({ color: bc });
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// 메인 조합
// ═══════════════════════════════════════════════════════════════════════════
export function drawBackground(g: PIXI.Graphics) {
  // 전체 배경
  g.rect(0, 0, CANVAS.WIDTH, CANVAS.HEIGHT).fill({ color: 0x08080f });

  // 오피스 배경
  g.rect(OFFICE.x, OFFICE.y, OFFICE.w, OFFICE.h).fill({ color: 0x0a0a14 });

  drawCorridor(g);

  for (const room of Object.values(ROOMS)) {
    drawRoom(g, room);
  }
  drawRoomDividers(g);

  drawDashboard(g);
  drawHeader(g);
  drawFooter(g);
}
