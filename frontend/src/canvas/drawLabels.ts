import * as PIXI from "pixi.js";
import { ROOMS, CANVAS } from "../config/layout";

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

// ── 팀 방 레이블 (이미지 위 오버레이) ───────────────────────────────────────
export function drawRoomLabels(c: PIXI.Container) {
  for (const room of Object.values(ROOMS)) {
    // 반투명 배경 바
    const bg = new PIXI.Graphics();
    bg.rect(room.x + 4, room.y + 4, 90, 16).fill({ color: 0x000000 });
    bg.alpha = 0.5;
    c.addChild(bg);

    txt(c, room.labelEn, room.x + 8, room.y + 5, 8, room.accentColor, true);
    txt(c, room.label, room.x + 8, room.y + 14, 7, 0xcccccc);
  }
}

// ── 하단 상태바 ─────────────────────────────────────────────────────────────
export function drawFooterLabels(c: PIXI.Container) {
  // 반투명 바
  const bg = new PIXI.Graphics();
  bg.rect(0, CANVAS.HEIGHT - 20, CANVAS.WIDTH, 20).fill({ color: 0x000000 });
  bg.alpha = 0.6;
  c.addChild(bg);

  const items = [
    { x: 10,  text: "● PREFECT",  color: 0x4caf50 },
    { x: 98,  text: "● MLFLOW",   color: 0x2196f3 },
    { x: 178, text: "● SUPABASE", color: 0xff9800 },
    { x: 274, text: "● TELEGRAM", color: 0x29b6f6 },
    { x: 370, text: "● KRX",      color: 0xf44336 },
  ];

  const y = CANVAS.HEIGHT - 17;
  for (const item of items) {
    txt(c, item.text, item.x, y, 8, item.color);
  }

  const now = new Date().toLocaleString("ko-KR", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  txt(c, now, CANVAS.WIDTH - 72, y, 8, 0x999999);
}
