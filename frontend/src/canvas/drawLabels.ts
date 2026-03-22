import * as PIXI from "pixi.js";
import { ROOMS, DASHBOARD, CANVAS, FOOTER } from "../config/layout";

const MONO: Partial<PIXI.TextStyle> = {
  fontFamily: '"Courier New", "Lucida Console", monospace',
};

function txt(
  container: PIXI.Container,
  text: string,
  x: number,
  y: number,
  size: number,
  color: number,
  bold = false,
) {
  const t = new PIXI.Text({
    text,
    style: { ...MONO, fontSize: size, fill: color, fontWeight: bold ? "bold" : "normal" },
  });
  t.x = x;
  t.y = y;
  container.addChild(t);
  return t;
}

// ── 팀 방 레이블 ─────────────────────────────────────────────────────────────
export function drawRoomLabels(c: PIXI.Container) {
  for (const room of Object.values(ROOMS)) {
    // 영문 약칭 (굵게)
    txt(c, room.labelEn, room.x + 8, room.y + 5, 8, room.accentColor, true);
    // 한글명 (옅게)
    txt(c, room.label, room.x + 68, room.y + 5, 7, room.accentColor & 0xaaaaaa);
  }
}

// ── 헤더 마켓 데이터 ─────────────────────────────────────────────────────────
export function drawHeaderLabels(c: PIXI.Container) {
  const items = [
    { x: 11,  name: "KOSPI",   value: "2,730.45", delta: "+0.32%", up: true  },
    { x: 171, name: "KOSDAQ",  value: "875.12",   delta: "-0.11%", up: false },
    { x: 331, name: "USD/KRW", value: "1,328.5",  delta: "+2.10",  up: false },
  ];

  for (const item of items) {
    txt(c, item.name,  item.x + 5,  7, 7, 0x5566aa);
    txt(c, item.value, item.x + 44, 7, 9, 0xccd8ff, true);
    txt(c, item.delta, item.x + 108, 7, 8, item.up ? 0x66cc66 : 0xff5555);
  }

  // 타이틀
  txt(c, "AI DATA SCIENCE TEAM", CANVAS.WIDTH - 200, 9, 9, 0x334466, true);

  // 시스템 도트 레이블
  const dotLabels = ["PRE", "ML", "DB", "TG"];
  dotLabels.forEach((label, i) => {
    txt(c, label, CANVAS.WIDTH - 122 + i * 20, 20, 6, 0x334455);
  });
}

// ── 대시보드 패널 레이블 ─────────────────────────────────────────────────────
export function drawDashboardLabels(c: PIXI.Container) {
  const { x, y, h } = DASHBOARD;
  const panelH = Math.floor((h - 24) / 4) - 4;
  const panels = [
    { label: "MARKET OVERVIEW",  sub: "KOSPI · KOSDAQ",      color: 0x4caf50 },
    { label: "ML MODELS",        sub: "Prophet · LSTM · XGB", color: 0xe91e63 },
    { label: "BACKTEST",         sub: "Sharpe · MDD · WR",   color: 0x009688 },
    { label: "REPORTS",          sub: "종합 · 투자메모 · 리스크", color: 0x9c27b0 },
  ];

  panels.forEach((p, i) => {
    const py = y + 8 + i * (panelH + 6);
    txt(c, p.label, x + 16, py + 7,  8, p.color, true);
    txt(c, p.sub,   x + 16, py + 17, 7, p.color & 0x888888);
  });
}

// ── 푸터 상태 ────────────────────────────────────────────────────────────────
export function drawFooterLabels(c: PIXI.Container) {
  const y = CANVAS.HEIGHT - FOOTER.HEIGHT + 7;
  const items = [
    { x: 10,  text: "● PREFECT",  color: 0x4caf50 },
    { x: 98,  text: "● MLFLOW",   color: 0x2196f3 },
    { x: 178, text: "● SUPABASE", color: 0xff9800 },
    { x: 274, text: "● TELEGRAM", color: 0x29b6f6 },
    { x: 370, text: "● KRX",      color: 0xf44336 },
  ];

  for (const item of items) {
    txt(c, item.text, item.x, y, 8, item.color);
  }

  const now = new Date().toLocaleString("ko-KR", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  txt(c, now, CANVAS.WIDTH - 72, y, 8, 0x334455);
}
