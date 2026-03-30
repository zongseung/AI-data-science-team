import * as PIXI from "pixi.js";
import { ROOMS, type RoomKey } from "../config/layout";
import { darken, lighten } from "./colorUtils";

// ── 에이전트 상태 ────────────────────────────────────────────────────────────
export type AgentState = "idle" | "working" | "thinking";

// ── 에이전트 정의 ────────────────────────────────────────────────────────────
interface AgentDef {
  id: string;
  name: string;
  room: RoomKey;
  offsetX: number; // 방 내부 상대 좌표
  offsetY: number;
  hairColor: number;
  skinColor: number;
  facing: "down" | "up";
}

const AGENTS: AgentDef[] = [
  // 수집팀 (3명)
  { id: "collector_krx",   name: "KRX수집",     room: "collection", offsetX: 50,  offsetY: 80, hairColor: 0x332200, skinColor: 0xf0c8a0, facing: "down" },
  { id: "collector_hl",    name: "HL수집",      room: "collection", offsetX: 115, offsetY: 80, hairColor: 0x1a1a2a, skinColor: 0xdeb896, facing: "down" },
  { id: "collector_news",  name: "뉴스수집",    room: "collection", offsetX: 180, offsetY: 80, hairColor: 0x442200, skinColor: 0xf0c8a0, facing: "down" },

  // 분석팀 (3명)
  { id: "analyst_tech",    name: "기술분석",    room: "analysis", offsetX: 50,  offsetY: 80, hairColor: 0x222222, skinColor: 0xdeb896, facing: "down" },
  { id: "analyst_fund",    name: "펀더멘털",    room: "analysis", offsetX: 115, offsetY: 80, hairColor: 0x553322, skinColor: 0xf0c8a0, facing: "down" },
  { id: "analyst_sent",    name: "감성분석",    room: "analysis", offsetX: 180, offsetY: 80, hairColor: 0x1a1a2a, skinColor: 0xe8c0a0, facing: "down" },

  // ML팀 (3명)
  { id: "ml_prophet",      name: "예측",        room: "ml", offsetX: 50,  offsetY: 80, hairColor: 0x332200, skinColor: 0xdeb896, facing: "down" },
  { id: "ml_backtest",     name: "백테스트",    room: "ml", offsetX: 115, offsetY: 80, hairColor: 0x222222, skinColor: 0xf0c8a0, facing: "down" },
  { id: "ml_risk",         name: "리스크",      room: "ml", offsetX: 180, offsetY: 80, hairColor: 0x442200, skinColor: 0xe8c0a0, facing: "down" },

  // 보고서팀 (3명)
  { id: "report_writer",   name: "종합보고",    room: "report", offsetX: 50,  offsetY: 80, hairColor: 0x1a1a2a, skinColor: 0xf0c8a0, facing: "down" },
  { id: "report_memo",     name: "투자메모",    room: "report", offsetX: 115, offsetY: 80, hairColor: 0x553322, skinColor: 0xdeb896, facing: "down" },
  { id: "report_editor",   name: "편집장",      room: "report", offsetX: 180, offsetY: 80, hairColor: 0x222222, skinColor: 0xe8c0a0, facing: "down" },
];

// ── 픽셀 캐릭터 그리기 (앉은 자세, ~10×14px) ────────────────────────────────
function drawSittingCharacter(
  g: PIXI.Graphics,
  x: number,
  y: number,
  agent: AgentDef,
  state: AgentState,
) {
  const { hairColor, skinColor } = agent;
  const bodyColor = ROOMS[agent.room].accentColor;

  // 머리카락
  g.rect(x + 1, y, 8, 3).fill({ color: hairColor });
  g.rect(x + 0, y + 1, 1, 2).fill({ color: hairColor });
  g.rect(x + 9, y + 1, 1, 2).fill({ color: hairColor });

  // 얼굴
  g.rect(x + 1, y + 3, 8, 5).fill({ color: skinColor });
  // 눈
  g.rect(x + 3, y + 5, 1, 1).fill({ color: 0x222222 });
  g.rect(x + 6, y + 5, 1, 1).fill({ color: 0x222222 });

  // 몸통 (팀 색상)
  const shirt = state === "working" ? lighten(bodyColor, 0.15) : bodyColor;
  g.rect(x + 1, y + 8, 8, 5).fill({ color: shirt });
  // 어깨
  g.rect(x - 1, y + 8, 2, 4).fill({ color: darken(shirt, 0.15) });
  g.rect(x + 9, y + 8, 2, 4).fill({ color: darken(shirt, 0.15) });

  // thinking 상태: 말풍선
  if (state === "thinking") {
    g.circle(x + 12, y - 2, 1.5).fill({ color: 0xffffff });
    g.circle(x + 14, y - 5, 2).fill({ color: 0xffffff });
    g.rect(x + 11, y - 12, 14, 8)
      .fill({ color: 0xffffff })
      .stroke({ color: 0x888888, width: 1 });
    g.rect(x + 13, y - 11, 2, 1).fill({ color: 0x666666 });
    g.rect(x + 13, y - 9, 6, 1).fill({ color: 0x666666 });
    g.rect(x + 13, y - 7, 4, 1).fill({ color: 0x666666 });
  }

  // working 상태: 밝기 표시 점
  if (state === "working") {
    g.circle(x + 5, y - 3, 2).fill({ color: 0x4caf50 });
  }
}

// ── 전체 캐릭터 배치 ────────────────────────────────────────────────────────
export function drawAllCharacters(
  g: PIXI.Graphics,
  states?: Map<string, AgentState>,
) {
  for (const agent of AGENTS) {
    const room = ROOMS[agent.room];
    const absX = room.x + agent.offsetX;
    const absY = room.y + agent.offsetY;
    const state = states?.get(agent.id) ?? "idle";
    drawSittingCharacter(g, absX, absY, agent, state);
  }
}

export { AGENTS };
